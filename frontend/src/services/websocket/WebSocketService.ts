import { Observable, Subject, ReplaySubject } from 'rxjs';
import { filter } from 'rxjs/operators';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

interface WebSocketMessage {
  type: string;
  tenantId: string;
  payload: any;
  timestamp: string;
}

interface SubscriptionConfig {
  tenantId: string;
  types: string[];
}

class WebSocketService {
  private socket$: WebSocketSubject<WebSocketMessage> | null = null;
  private messageSubject = new Subject<WebSocketMessage>();
  private connectionStatus = new ReplaySubject<boolean>(1);
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  
  constructor(private url: string) {}
  
  connect(): void {
    if (this.socket$ && !this.socket$.closed) {
      return;
    }
    
    this.socket$ = webSocket({
      url: this.url,
      openObserver: {
        next: () => {
          console.log('WebSocket connected');
          this.connectionStatus.next(true);
          this.reconnectAttempts = 0;
        }
      },
      closeObserver: {
        next: () => {
          console.log('WebSocket disconnected');
          this.connectionStatus.next(false);
          this.handleReconnect();
        }
      }
    });
    
    this.socket$.subscribe({
      next: (message: WebSocketMessage) => {
        this.messageSubject.next(message);
        this.handleMessage(message);
      },
      error: (error) => {
        console.error('WebSocket error:', error);
        this.connectionStatus.next(false);
      }
    });
  }
  
  disconnect(): void {
    if (this.socket$) {
      this.socket$.complete();
      this.socket$ = null;
    }
  }
  
  send(message: WebSocketMessage): void {
    if (this.socket$ && !this.socket$.closed) {
      this.socket$.next(message);
    } else {
      console.warn('WebSocket not connected');
    }
  }
  
  subscribeToTypes(config: SubscriptionConfig): Observable<WebSocketMessage> {
    // Send subscription request
    this.send({
      type: 'SUBSCRIBE',
      tenantId: config.tenantId,
      payload: { types: config.types },
      timestamp: new Date().toISOString()
    });
    
    // Return filtered messages
    return this.messageSubject.asObservable().pipe(
      filter(message => 
        message.tenantId === config.tenantId && 
        config.types.includes(message.type)
      )
    );
  }
  
  getConnectionStatus(): Observable<boolean> {
    return this.connectionStatus.asObservable();
  }
  
  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      
      console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      
      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }
  
  private handleMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'VIOLATION_CREATED':
        this.handleViolationCreated(message.payload);
        break;
      case 'VIOLATION_UPDATED':
        this.handleViolationUpdated(message.payload);
        break;
      case 'POLICY_UPDATED':
        this.handlePolicyUpdated(message.payload);
        break;
      case 'RESOURCE_UPDATED':
        this.handleResourceUpdated(message.payload);
        break;
      case 'SYSTEM_ALERT':
        this.handleSystemAlert(message.payload);
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }
  
  private handleViolationCreated(violation: any): void {
    // Update local state/store
    // Show notification
    this.showNotification({
      title: 'New Violation Detected',
      message: `${violation.policyName} - ${violation.resourceName}`,
      severity: violation.severity,
      action: () => {
        // Navigate to violation details
        window.location.href = `/violations/${violation.id}`;
      }
    });
  }
  
  private handleSystemAlert(alert: any): void {
    this.showNotification({
      title: 'System Alert',
      message: alert.message,
      severity: 'warning',
      autoHide: false
    });
  }
  
  private showNotification(notification: any): void {
    // Dispatch to notification system
    const event = new CustomEvent('sky-notification', {
      detail: notification
    });
    window.dispatchEvent(event);
  }
}

export default WebSocketService;
