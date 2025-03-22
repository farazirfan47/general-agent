import React from 'react';

interface StatusUpdate {
  id: string;
  type: 'thinking' | 'web_search' | 'computer_use' | 'cua_event' | 'cua_reasoning' | 'step' | 'plan';
  message: string;
  details?: any;
  timestamp: Date;
}

interface StatusIndicatorProps {
  updates: StatusUpdate[];
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ updates }) => {
  const [isCollapsed, setIsCollapsed] = React.useState(false);

  // Filter updates but keep CUA events and reasoning
  const filteredUpdates = updates.filter((update, index, array) => {
    // Keep all step updates
    if (update.type === 'step') return true;
    
    // For thinking updates, only keep the most recent one
    if (update.type === 'thinking') {
      const lastThinkingIndex = array
        .map((u, i) => u.type === 'thinking' ? i : -1)
        .filter(i => i !== -1)
        .pop();
      return index === lastThinkingIndex;
    }
    
    // Keep all browser-related events
    if (update.type === 'computer_use' || 
        update.type === 'web_search' || 
        update.type === 'cua_event' || 
        update.type === 'cua_reasoning') {
      return true;
    }
    
    // Filter out plan and other updates
    return false;
  });

  // Group updates by step number if available
  const stepUpdates = filteredUpdates.filter(update => 
    update.type === 'step' && update.details && update.details.current
  );
  
  // Get the current step number
  const currentStepNumber = stepUpdates.length > 0 
    ? Math.max(...stepUpdates.map(update => update.details.current))
    : 0;
  
  // Get the total number of steps
  const totalSteps = stepUpdates.length > 0 
    ? stepUpdates[0].details.total 
    : 0;

  return (
    <div className="w-full max-w-2xl rounded-lg p-4 bg-gray-50 border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          <div className="mr-2 h-2 w-2 bg-gray-700 rounded-full"></div>
          <h3 className="text-sm font-medium text-gray-700">Processing your request</h3>
        </div>
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="text-gray-500 hover:text-gray-700 transition-colors"
        >
          {isCollapsed ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
            </svg>
          )}
        </button>
      </div>
      
      {totalSteps > 0 && (
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Progress</span>
            <span>{currentStepNumber} of {totalSteps} steps</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div 
              className="bg-gray-700 h-1.5 rounded-full" 
              style={{ width: `${(currentStepNumber / totalSteps) * 100}%` }}
            ></div>
          </div>
        </div>
      )}
      
      {!isCollapsed && (
        <div className="space-y-0 mt-4">
          {/* Timeline of steps */}
          <div className="relative">
            {filteredUpdates.map((update, index) => {
              // Determine if this step is the current one being processed
              const isCurrentStep = update.type === 'step' && 
                update.details?.current === currentStepNumber && 
                update.details?.current !== update.details?.total;
              
              // Determine if this step is completed
              const isCompleted = update.type === 'step' && 
                update.details?.current < currentStepNumber;
              
              // Determine icon and styling based on update type
              let iconClass = "bg-gray-400";
              let textClass = "text-gray-700";
              
              if (update.type === 'step') {
                if (isCurrentStep) {
                  iconClass = "bg-gray-700";
                  textClass = "text-gray-800 font-medium";
                } else if (isCompleted) {
                  iconClass = "bg-gray-600";
                  textClass = "text-gray-700";
                }
              } else if (update.type === 'cua_event') {
                iconClass = "bg-gray-600";
                textClass = "text-gray-700";
              } else if (update.type === 'cua_reasoning') {
                iconClass = "bg-gray-600";
                textClass = "text-gray-700";
              } else if (update.type === 'web_search') {
                iconClass = "bg-gray-600";
                textClass = "text-gray-700";
              } else if (update.type === 'thinking') {
                textClass = "text-gray-700";
              }
              
              return (
                <div key={update.id} className="flex items-start py-2 relative">
                  {/* Timeline connector line */}
                  {index < filteredUpdates.length - 1 && (
                    <div className="absolute left-[9px] top-[18px] w-[2px] bg-gray-300 h-[calc(100%)]"></div>
                  )}
                  
                  {/* Status icon */}
                  <div className={`relative z-10 mt-1 mr-3 h-[18px] w-[18px] rounded-full flex items-center justify-center ${iconClass}`}>
                    {isCompleted && update.type === 'step' && (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                    {isCurrentStep && (
                      <div className="h-2 w-2 bg-white rounded-full"></div>
                    )}
                    {update.type === 'cua_event' && (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                        <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                      </svg>
                    )}
                    {update.type === 'cua_reasoning' && (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2h-1V9a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    )}
                    {update.type === 'web_search' && (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  
                  {/* Status content */}
                  <div className="flex-1">
                    <div className={`text-sm ${textClass}`}>
                      {update.message}
                    </div>
                    
                    {/* Show details for different update types */}
                    {update.details && (
                      <div className="mt-0.5 text-xs text-gray-500">
                        {update.type === 'web_search' && update.details.query && (
                          <span>Query: "{update.details.query}"</span>
                        )}
                        {update.type === 'computer_use' && update.details.action && (
                          <span>{update.details.action}</span>
                        )}
                        {update.type === 'cua_event' && update.details.action && (
                          <span>{update.details.element || update.details.description || update.details.action}</span>
                        )}
                        {update.type === 'cua_reasoning' && update.details.text && (
                          <span className="italic">{update.details.text.length > 100 ? update.details.text.substring(0, 100) + '...' : update.details.text}</span>
                        )}
                      </div>
                    )}
                    
                    {/* Show loading animation for current step */}
                    {isCurrentStep && (
                      <div className="mt-1 flex items-center text-xs text-gray-500">
                        <div className="flex space-x-1 mr-2">
                          <div className="h-1.5 w-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                          <div className="h-1.5 w-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                          <div className="h-1.5 w-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                        <span>In progress</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default StatusIndicator; 