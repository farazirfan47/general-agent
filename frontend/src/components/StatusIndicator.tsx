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
    <div className="w-full max-w-2xl bg-zinc-900 rounded-lg p-4 text-white">
      <div className="flex items-center mb-3">
        <div className="animate-pulse mr-2">
          <div className="h-2 w-2 bg-blue-500 rounded-full"></div>
        </div>
        <h3 className="text-sm font-medium">Processing your request</h3>
      </div>
      
      {totalSteps > 0 && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-zinc-400 mb-1">
            <span>Progress</span>
            <span>{currentStepNumber} of {totalSteps} steps</span>
          </div>
          <div className="w-full bg-zinc-800 rounded-full h-1.5">
            <div 
              className="bg-blue-500 h-1.5 rounded-full" 
              style={{ width: `${(currentStepNumber / totalSteps) * 100}%` }}
            ></div>
          </div>
        </div>
      )}
      
      <div className="space-y-3 mt-4">
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
            let iconClass = "bg-zinc-700";
            let textClass = "text-zinc-300";
            
            if (update.type === 'step') {
              if (isCurrentStep) {
                iconClass = "bg-blue-500";
                textClass = "text-blue-400 font-medium";
              } else if (isCompleted) {
                iconClass = "bg-green-500";
              }
            } else if (update.type === 'cua_event') {
              iconClass = "bg-purple-500";
              textClass = "text-purple-300";
            } else if (update.type === 'cua_reasoning') {
              iconClass = "bg-yellow-500";
              textClass = "text-yellow-300";
            } else if (update.type === 'web_search') {
              iconClass = "bg-orange-500";
              textClass = "text-orange-300";
            }
            
            return (
              <div key={update.id} className="flex items-start mb-3 relative">
                {/* Timeline connector line */}
                {index < filteredUpdates.length - 1 && (
                  <div className="absolute left-[9px] top-[18px] w-[2px] bg-zinc-700 h-[calc(100%+4px)]"></div>
                )}
                
                {/* Status icon */}
                <div className={`relative z-10 mt-1 mr-3 h-[18px] w-[18px] rounded-full flex items-center justify-center ${iconClass}`}>
                  {isCompleted && update.type === 'step' && (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                  {isCurrentStep && (
                    <div className="h-2 w-2 bg-white rounded-full animate-pulse"></div>
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
                  
                  {/* Show loading animation for current step */}
                  {isCurrentStep && (
                    <div className="mt-1 flex items-center text-xs text-zinc-400">
                      <div className="flex space-x-1 mr-2">
                        <div className="h-1.5 w-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="h-1.5 w-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="h-1.5 w-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                      <span>In progress</span>
                    </div>
                  )}
                  
                  {/* Show details for different update types */}
                  {update.details && (
                    <div className="mt-1 text-xs text-zinc-400">
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
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default StatusIndicator; 