import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResourceGraph from '../../components/visualization/ResourceGraph';

// Mock vis-network
jest.mock('vis-network/standalone', () => ({
  DataSet: jest.fn().mockImplementation(() => ({
    add: jest.fn(),
    remove: jest.fn(),
    update: jest.fn(),
    get: jest.fn(),
    length: 0
  })),
  Network: jest.fn().mockImplementation(() => ({
    on: jest.fn(),
    off: jest.fn(),
    destroy: jest.fn(),
    fit: jest.fn(),
    moveTo: jest.fn(),
    selectNodes: jest.fn(),
    focus: jest.fn()
  }))
}));

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({
      nodes: [
        {
          id: 'resource-1',
          name: 'Web Server',
          type: 'aws:ec2:instance',
          cloud: 'aws',
          region: 'us-east-1',
          violations: 0
        }
      ],
      edges: [
        {
          source: 'resource-1',
          target: 'resource-2',
          type: 'CONNECTED_TO',
          strength: 1
        }
      ]
    })
  })
) as jest.Mock;

describe('ResourceGraph', () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
  });
  
  it('renders graph container', () => {
    render(<ResourceGraph tenantId="test-tenant" />);
    
    expect(screen.getByTestId('graph-container')).toBeInTheDocument();
  });
  
  it('handles search functionality', async () => {
    render(<ResourceGraph tenantId="test-tenant" />);
    
    // Wait for graph to load
    await screen.findByTestId('graph-container');
    
    const searchInput = screen.getByPlaceholderText('Search resources...');
    fireEvent.change(searchInput, { target: { value: 'Web' } });
    fireEvent.keyPress(searchInput, { key: 'Enter', code: 'Enter' });
    
    // Verify search was triggered
    expect(global.fetch).toHaveBeenCalled();
  });
  
  it('displays loading state', () => {
    (global.fetch as jest.Mock).mockImplementationOnce(
      () => new Promise(() => {}) // Never resolves
    );
    
    render(<ResourceGraph tenantId="test-tenant" />);
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
  
  it('displays error state', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() =>
      Promise.reject(new Error('Network error'))
    );
    
    render(<ResourceGraph tenantId="test-tenant" />);
    
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });
});
