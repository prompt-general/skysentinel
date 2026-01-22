describe('Dashboard E2E Tests', () => {
  beforeEach(() => {
    // Mock API responses
    cy.intercept('POST', '/graphql', (req) => {
      if (req.body.operationName === 'DashboardOverview') {
        req.reply({
          data: {
            dashboardOverview: {
              metrics: {
                totalResources: 1000,
                totalViolations: 25,
                criticalViolations: 3,
                complianceScore: 92.5
              },
              recentViolations: [],
              complianceTrend: [],
              mlInsights: {
                highRiskPredictions: 0,
                modelAccuracy: 0.95,
                driftDetected: false
              }
            }
          }
        });
      }
    });
    
    // Login
    cy.visit('/login');
    cy.get('[data-testid="email"]').type('admin@skysentinel.io');
    cy.get('[data-testid="password"]').type('password123');
    cy.get('[data-testid="login-button"]').click();
  });
  
  it('loads dashboard successfully', () => {
    cy.url().should('include', '/dashboard');
    cy.contains('Security Dashboard').should('be.visible');
    cy.contains('Total Resources').should('be.visible');
    cy.contains('Total Violations').should('be.visible');
  });
  
  it('navigates to violations page', () => {
    cy.get('[data-testid="nav-violations"]').click();
    cy.url().should('include', '/violations');
    cy.contains('Violations').should('be.visible');
  });
  
  it('filters violations by severity', () => {
    cy.visit('/violations');
    cy.get('[data-testid="severity-filter"]').click();
    cy.contains('Critical').click();
    cy.get('[data-testid="apply-filters"]').click();
    
    // Verify filter was applied
    cy.get('[data-testid="violation-severity"]').each(($el) => {
      expect($el.text()).to.include('CRITICAL');
    });
  });
  
  it('creates a new policy', () => {
    cy.visit('/policies');
    cy.get('[data-testid="create-policy-button"]').click();
    
    // Fill policy form
    cy.get('[data-testid="policy-name"]').type('Test Policy');
    cy.get('[data-testid="policy-description"]').type('Test description');
    cy.get('[data-testid="policy-severity"]').click();
    cy.contains('High').click();
    
    // Save policy
    cy.get('[data-testid="save-policy-button"]').click();
    
    // Verify policy was created
    cy.contains('Test Policy').should('be.visible');
  });
  
  it('visualizes attack paths', () => {
    cy.visit('/attack-paths');
    cy.contains('Attack Paths').should('be.visible');
    
    // Wait for graph to load
    cy.get('[data-testid="attack-path-graph"]', { timeout: 10000 }).should('be.visible');
    
    // Click on a node
    cy.get('[data-testid="graph-node"]').first().click();
    
    // Verify node details are shown
    cy.get('[data-testid="node-details"]').should('be.visible');
  });
});
