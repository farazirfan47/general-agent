import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "AI Chat Assistant",
  description: "Chat with an AI assistant that provides real-time updates and can use web search and browser tools.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <div className="flex h-screen bg-gray-200 w-full flex-col text-stone-900">
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
