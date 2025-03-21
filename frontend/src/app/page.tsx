'use client';

import dynamic from 'next/dynamic';

// Dynamically import Chat component with no SSR to avoid NextRouter mounting issues
const Chat = dynamic(() => import('@/components/Chat'), { 
  ssr: false 
});

export default function Home() {
  return (
    <main className="h-screen overflow-hidden bg-gray-200">
      <Chat />
    </main>
  );
}
