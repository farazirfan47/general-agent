cua_tool = {
  "type": "function",
  "name": "computer_use",
  "description": "Performs interactive browser tasks in a sandboxed environment. Use this tool ONLY for tasks requiring direct browser interaction (clicking, scrolling, form-filling, etc.) rather than simple information retrieval. For basic information searches, use the separate web_search tool instead.",
  "parameters": {
    "type": "object",
    "properties": {
      "task": {
        "type": "string",
        "description": "Detailed description of the interactive browser task to perform. Examples: 'navigate to example.com and click on the Products tab', 'fill out a login form on website.com with the provided credentials', 'scroll through a social media feed and take a screenshot', 'interact with a web application that requires clicking specific elements'."
      }
    },
    "required": [
      "task"
    ],
    "additionalProperties": False
  }
}