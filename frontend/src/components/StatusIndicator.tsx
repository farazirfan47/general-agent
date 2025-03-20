import React from 'react';

interface StatusIndicatorProps {
  type: 'thinking' | 'web_search' | 'computer_use' | 'cua_event' | 'step' | 'plan';
  message: string;
  details?: any;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ type, message, details }) => {
  // Different styles and icons based on the type
  const getIconAndColor = () => {
    switch (type) {
      case 'thinking':
        return { 
          icon: '🤔', 
          bgColor: 'bg-yellow-100 dark:bg-yellow-900/30', 
          textColor: 'text-yellow-800 dark:text-yellow-200' 
        };
      case 'web_search':
        return { 
          icon: '🔎', 
          bgColor: 'bg-blue-100 dark:bg-blue-900/30', 
          textColor: 'text-blue-800 dark:text-blue-200' 
        };
      case 'computer_use':
        return { 
          icon: '💻', 
          bgColor: 'bg-purple-100 dark:bg-purple-900/30', 
          textColor: 'text-purple-800 dark:text-purple-200' 
        };
      case 'cua_event':
        return { 
          icon: '⌨️', 
          bgColor: 'bg-indigo-100 dark:bg-indigo-900/30', 
          textColor: 'text-indigo-800 dark:text-indigo-200' 
        };
      case 'step':
        return { 
          icon: '✅', 
          bgColor: 'bg-green-100 dark:bg-green-900/30', 
          textColor: 'text-green-800 dark:text-green-200' 
        };
      case 'plan':
        return { 
          icon: '📝', 
          bgColor: 'bg-orange-100 dark:bg-orange-900/30', 
          textColor: 'text-orange-800 dark:text-orange-200' 
        };
      default:
        return { 
          icon: 'ℹ️', 
          bgColor: 'bg-gray-100 dark:bg-gray-800', 
          textColor: 'text-gray-800 dark:text-gray-200' 
        };
    }
  };

  const { icon, bgColor, textColor } = getIconAndColor();

  // Format CUA event details for display
  const formatCuaEventDetails = () => {
    if (type !== 'cua_event' || !details) return null;

    const { action } = details;
    
    switch(action) {
      case 'click':
        return `Clicked at x:${details.x}, y:${details.y}`;
      case 'type':
        return `Typing: "${details.text}"`;
      case 'keypress':
        return `Pressed key: ${details.keys?.join(' + ')}`;
      case 'scroll':
        return `Scrolling ${details.direction}`;
      default:
        return `${action} action`;
    }
  };

  return (
    <div className={`flex items-center p-2 rounded ${bgColor} ${textColor} text-sm my-1`}>
      <span className="mr-2">{icon}</span>
      <div className="flex-1">
        <div className="font-medium">{message}</div>
        
        {type === 'cua_event' && (
          <div className="text-xs opacity-80 mt-1">
            {formatCuaEventDetails()}
          </div>
        )}
        
        {type === 'step' && details && (
          <div className="text-xs opacity-80 mt-1">
            Step {details.current}/{details.total}: {details.description}
          </div>
        )}
        
        {type === 'plan' && details?.plan && (
          <div className="text-xs opacity-80 mt-1">
            Plan created with {details.plan.length} steps
          </div>
        )}
      </div>
    </div>
  );
};

export default StatusIndicator; 