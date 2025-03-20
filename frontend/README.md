# AI Chatbot Frontend

A Next.js frontend for an AI chatbot with real-time updates and conversation sharing capabilities.

## Features

- Real-time chat with AI assistant
- Visual indicators for different agent actions:
  - Thinking state
  - Plan display
  - Step-by-step execution
  - Web search tool usage
  - Computer/browser tool usage
  - Browser actions (click, scroll, type, etc.)
- Session persistence
- Shareable conversation links
- Responsive UI with dark mode support

## Tech Stack

- Next.js 14
- React 18
- TypeScript
- TailwindCSS
- WebSocket for real-time updates

## Getting Started

1. Clone the repository
2. Install dependencies:

```bash
cd frontend
npm install
```

3. Start the development server:

```bash
npm run dev
```

4. Make sure the FastAPI backend is running at http://localhost:8000

## API Integration

The frontend communicates with the FastAPI backend using:

1. REST API for session retrieval
2. WebSockets for real-time updates and message streaming

## Deployment

To build the application for production:

```bash
npm run build
```

Then start the production server:

```bash
npm start
```

## Project Structure

- `src/app`: Next.js App Router pages
- `src/components`: React components
- `src/lib`: Utilities and helpers
- `src/styles`: Global CSS and Tailwind config

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
