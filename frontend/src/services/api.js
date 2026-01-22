import { ApolloClient, InMemoryCache, createHttpLink, split } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';
import { getMainDefinition } from '@apollo/client/utilities';
import { GraphQLWsLink } from '@apollo/client/link/subscriptions';
import { createClient } from 'graphql-ws';

// HTTP Link for queries and mutations
const httpLink = createHttpLink({
  uri: process.env.REACT_APP_GRAPHQL_URL || 'http://localhost:8000/graphql',
  credentials: 'include',
});

// WebSocket Link for subscriptions
const wsLink = new GraphQLWsLink(
  createClient({
    url: process.env.REACT_APP_GRAPHQL_WS_URL || 'ws://localhost:8000/ws',
    connectionParams: () => {
      const token = localStorage.getItem('authToken');
      const tenantId = localStorage.getItem('tenantId');
      return {
        authorization: token ? `Bearer ${token}` : '',
        'X-Tenant-ID': tenantId || 'default-tenant',
      };
    },
  })
);

// Split link based on operation type
const splitLink = split(
  ({ query }) => {
    const definition = getMainDefinition(query);
    return (
      definition.kind === 'OperationDefinition' &&
      definition.operation === 'subscription'
    );
  },
  wsLink,
  httpLink
);

// Auth link for adding headers
const authLink = setContext((_, { headers }) => {
  const token = localStorage.getItem('authToken');
  const tenantId = localStorage.getItem('tenantId');
  
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : '',
      'X-Tenant-ID': tenantId || 'default-tenant',
    },
  };
});

// Apollo Client configuration
const client = new ApolloClient({
  link: authLink.concat(splitLink),
  cache: new InMemoryCache({
    typePolicies: {
      Query: {
        fields: {
          // Custom field policies for caching
          overview: {
            merge(existing, incoming) {
              return incoming;
            },
          },
          policies: {
            keyArgs: ['filter', 'tenantId'],
            merge(existing = [], incoming, { args }) {
              // If no filter, replace entire cache
              if (!args.filter) {
                return incoming;
              }
              // Otherwise merge with existing
              return [...existing, ...incoming];
            },
          },
          violations: {
            keyArgs: ['filter', 'tenantId'],
            merge(existing = [], incoming, { args }) {
              if (!args.filter) {
                return incoming;
              }
              return [...existing, ...incoming];
            },
          },
          resources: {
            keyArgs: ['filter', 'tenantId'],
            merge(existing = [], incoming, { args }) {
              if (!args.filter) {
                return incoming;
              }
              return [...existing, ...incoming];
            },
          },
          evaluations: {
            keyArgs: ['filter', 'tenantId'],
            merge(existing = [], incoming, { args }) {
              if (!args.filter) {
                return incoming;
              }
              return [...existing, ...incoming];
            },
          },
        },
      },
      Policy: {
        keyFields: ['id'],
        fields: {
          violations: {
            merge(existing = [], incoming) {
              return [...incoming];
            },
          },
        },
      },
      Violation: {
        keyFields: ['id'],
        fields: {
          remediation: {
            merge(existing, incoming) {
              return incoming;
            },
          },
        },
      },
      Resource: {
        keyFields: ['id'],
        fields: {
          violations: {
            merge(existing = [], incoming) {
              return [...incoming];
            },
          },
          connections: {
            merge(existing = [], incoming) {
              return [...incoming];
            },
          },
        },
      },
      Evaluation: {
        keyFields: ['id'],
        fields: {
          violations: {
            merge(existing = [], incoming) {
              return [...incoming];
            },
          },
          recommendations: {
            merge(existing = [], incoming) {
              return [...incoming];
            },
          },
        },
      },
    },
  }),
  defaultOptions: {
    watchQuery: {
      errorPolicy: 'all',
      notifyOnNetworkStatusChange: true,
    },
    query: {
      errorPolicy: 'all',
    },
    mutate: {
      errorPolicy: 'all',
    },
  },
});

// Error handling
client.onResetStore(() => {
  // Clear cache on reset
  console.log('Apollo cache reset');
});

// Network status indicator
export const setupNetworkStatusIndicator = () => {
  let onlineStatus = navigator.onLine;

  window.addEventListener('online', () => {
    onlineStatus = true;
    client.reFetchObservableQueries();
  });

  window.addEventListener('offline', () => {
    onlineStatus = false;
  });

  return () => onlineStatus;
};

// Retry configuration for failed requests
export const retryLink = (operation, forward) => {
  return forward(operation).map(result => {
    if (result.errors) {
      const isNetworkError = result.errors.some(error => 
        error.message.includes('Network error') ||
        error.message.includes('Failed to fetch')
      );
      
      if (isNetworkError) {
        console.warn('Network error detected, retrying...');
        // Implement retry logic here
      }
    }
    return result;
  });
};

// Cache helpers
export const cacheHelpers = {
  // Clear specific type from cache
  clearType: (typeName) => {
    client.cache.modify({
      fields: (existing, { DELETE }) => {
        DELETE[typeName];
      },
    });
  },

  // Update specific item in cache
  updateItem: (typeName, item) => {
    client.cache.writeQuery({
      query: client.cache.readQuery({
        query: client.cache.config.typePolicies.Query.fields[typeName],
      }),
      data: item,
    });
  },

  // Evict specific item from cache
  evictItem: (typeName, id) => {
    client.cache.evict({
      id: `${typeName}:${id}`,
    });
  },

  // Reset entire cache
  resetCache: () => {
    client.resetStore();
  },
};

// Subscription helpers
export const subscriptionHelpers = {
  // Subscribe to violations
  subscribeToViolations: (tenantId, callback) => {
    return client.subscribe({
      query: gql`
        subscription ViolationSubscription($tenantId: String!) {
          violationCreated(tenantId: $tenantId) {
            id
            policy {
              id
              name
              severity
            }
            resource {
              id
              name
              type
              cloud
            }
            severity
            description
            timestamp
            status
            confidence
          }
        }
      `,
      variables: { tenantId },
    }).subscribe(callback);
  },

  // Subscribe to evaluations
  subscribeToEvaluations: (tenantId, callback) => {
    return client.subscribe({
      query: gql`
        subscription EvaluationSubscription($tenantId: String!) {
          evaluationCompleted(tenantId: $tenantId) {
            id
            type
            status
            result
            score
            confidence
            violations {
              id
              severity
              description
            }
            timestamp
            duration
            environment
            branch
            commit
          }
        }
      `,
      variables: { tenantId },
    }).subscribe(callback);
  },

  // Subscribe to compliance updates
  subscribeToCompliance: (tenantId, callback) => {
    return client.subscribe({
      query: gql`
        subscription ComplianceSubscription($tenantId: String!) {
          complianceUpdated(tenantId: $tenantId) {
            id
            overallScore
            status
            generatedAt
            timeframe
            tenantId
          }
        }
      `,
      variables: { tenantId },
    }).subscribe(callback);
  },
};

// Query helpers
export const queryHelpers = {
  // Refetch queries with specific type
  refetchQueries: (typeName) => {
    return client.refetchQueries({
      include: [typeName],
    });
  },

  // Get cached data
  getCachedData: (query, variables) => {
    try {
      return client.readQuery({ query, variables });
    } catch (error) {
      return null;
    }
  },

  // Write data to cache
  setCachedData: (query, variables, data) => {
    client.writeQuery({ query, variables, data });
  },
};

// Auth helpers
export const authHelpers = {
  // Set auth token
  setAuthToken: (token) => {
    localStorage.setItem('authToken', token);
    // Reset store to refetch with new token
    client.resetStore();
  },

  // Clear auth token
  clearAuthToken: () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('tenantId');
    client.resetStore();
  },

  // Set tenant ID
  setTenantId: (tenantId) => {
    localStorage.setItem('tenantId', tenantId);
    client.resetStore();
  },

  // Get current auth state
  getAuthState: () => {
    return {
      token: localStorage.getItem('authToken'),
      tenantId: localStorage.getItem('tenantId'),
    };
  },
};

// Export default client
export default client;

// Export configured link for custom usage
export { httpLink, wsLink, authLink, splitLink };
