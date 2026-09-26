import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from './Button';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[JourneyIQ ErrorBoundary] Uncaught runtime error:', error, errorInfo);
  }

  public handleReset = (): void => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public handleReload = (): void => {
    window.location.reload();
  };

  public render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-[380px] flex items-center justify-center p-6 w-full">
          <div className="card-soft p-8 text-center flex flex-col items-center justify-center max-w-lg w-full border border-red-200 bg-white shadow-card rounded-2xl">
            <div className="w-14 h-14 rounded-2xl bg-red-50 text-red-500 flex items-center justify-center mb-5 ring-8 ring-red-50/50">
              <AlertTriangle className="w-7 h-7" />
            </div>
            
            <h2 className="text-xl font-bold text-graphite-900 mb-2">
              Something went wrong
            </h2>
            
            <p className="text-sm text-gray-500 mb-6 max-w-md">
              A runtime rendering error occurred in this view. Your session and backend data remain intact.
            </p>

            {this.state.error?.message && (
              <div className="w-full text-left bg-gray-50 border border-gray-200 rounded-xl p-3 mb-6 overflow-x-auto text-xs font-mono text-gray-700 max-h-28">
                {this.state.error.message}
              </div>
            )}

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                size="sm"
                onClick={this.handleReset}
                icon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Try Again
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={this.handleReload}
                icon={<Home className="w-3.5 h-3.5" />}
              >
                Reload Page
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
