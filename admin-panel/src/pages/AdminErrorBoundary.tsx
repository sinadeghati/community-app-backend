import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";

type Props = {
  children: ReactNode;
};

type State = {
  error: Error | null;
};

export default class AdminErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Admin panel render error:", error, info.componentStack);
  }

  private handleRetry = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      return (
        <div className="admin-error-boundary panel">
          <h1>Something went wrong</h1>
          <p className="error">{this.state.error.message || "An unexpected error occurred."}</p>
          <div className="form-actions">
            <button type="button" onClick={this.handleRetry}>Try again</button>
            <Link to="/businesses" className="button-link secondary" onClick={this.handleRetry}>
              Back to businesses
            </Link>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
