import { AlertTriangle, RefreshCw, Trash2 } from 'lucide-react';
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[RAISE ErrorBoundary Caught]', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleResetAndReload = () => {
    try {
      localStorage.removeItem('raise-control-center-storage');
      localStorage.removeItem('raise_sessions');
      localStorage.removeItem('raise_active_session');
      localStorage.removeItem('raise_tunnel_url');
    } catch {
      // ignore
    }
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-[#090b10] text-slate-100 p-6 font-sans">
          <div className="w-full max-w-lg p-6 rounded-2xl bg-[#12151f] border border-rose-500/30 shadow-[0_0_50px_rgba(244,63,94,0.15)] space-y-4">
            <div className="flex items-center gap-3 border-b border-white/10 pb-4">
              <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400 shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-base font-bold text-white tracking-tight">
                  Workstation Interface Error
                </h1>
                <p className="text-xs text-slate-400">
                  A client-side render exception occurred. Your workspace data remains safe.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-black/60 border border-white/10 text-xs font-mono text-rose-300 max-h-40 overflow-y-auto break-all">
              {this.state.error?.message || 'Unknown runtime error'}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <button
                type="button"
                onClick={this.handleResetAndReload}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Clear Cache & Restart
              </button>

              <button
                type="button"
                onClick={this.handleReload}
                className="px-5 py-2 rounded-xl bg-white hover:bg-slate-200 text-black font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-sm active:scale-95"
              >
                <RefreshCw className="w-3.5 h-3.5 fill-black text-black" />
                Reload Workstation
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
