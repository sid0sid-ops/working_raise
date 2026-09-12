import React, { useState } from 'react';

export interface SplitPaneViewerProps {
  leftPane: React.ReactNode;
  rightPane?: React.ReactNode;
  isRightPaneOpen: boolean;
  onCloseRightPane: () => void;
  rightPaneTitle?: string;
  className?: string;
}

export const SplitPaneViewer: React.FC<SplitPaneViewerProps> = ({
  leftPane,
  rightPane,
  isRightPaneOpen,
  onCloseRightPane,
  rightPaneTitle = 'Document Preview',
  className = '',
}) => {
  const [isRightMaximized, setIsRightMaximized] = useState(false);

  return (
    <div
      data-testid="split-pane-viewer"
      className={`relative w-full h-full flex flex-col lg:flex-row overflow-hidden ${className}`}
    >
      {/* Left Pane (Chat Stream / Main Content) */}
      <div
        className={`w-full transition-all duration-200 flex flex-col min-w-0 ${
          isRightPaneOpen
            ? isRightMaximized
              ? 'hidden'
              : 'lg:w-1/2 xl:w-7/12 h-1/2 lg:h-full border-b lg:border-b-0 lg:border-r border-slate-200 dark:border-white/10'
            : 'w-full h-full'
        }`}
      >
        {leftPane}
      </div>

      {/* Right Pane (PDF Viewer / Document Workspace) */}
      {isRightPaneOpen && (
        <div
          data-testid="split-pane-right"
          className={`transition-all duration-200 flex flex-col bg-white dark:bg-[#0c0d12] min-w-0 z-20 ${
            isRightMaximized
              ? 'w-full h-full absolute inset-0 z-40'
              : 'w-full lg:w-1/2 xl:w-5/12 h-1/2 lg:h-full'
          }`}
        >
          {/* Header Bar */}
          <div className="h-10 px-3 border-b border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] flex items-center justify-between shrink-0 select-none">
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
              <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                {rightPaneTitle}
              </span>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setIsRightMaximized((prev) => !prev)}
                title={isRightMaximized ? 'Restore split view' : 'Maximize viewer'}
                aria-label={isRightMaximized ? 'Restore split view' : 'Maximize viewer'}
                className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/10 transition-colors cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {isRightMaximized ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 9L4 4m0 0l5 0m-5 0l0 5m11 11l5 0m0 0l0-5m0 5l-5-5" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4m0 0h4M4 4l5 5m11-5h-4m4 0v4m0-4l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  )}
                </svg>
              </button>

              <button
                type="button"
                onClick={onCloseRightPane}
                title="Close document viewer"
                aria-label="Close document viewer"
                className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/10 transition-colors cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Right Pane Body */}
          <div className="flex-1 min-h-0 overflow-auto">
            {rightPane}
          </div>
        </div>
      )}
    </div>
  );
};
