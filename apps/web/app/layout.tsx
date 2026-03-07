import './globals.css';
import type { ReactNode } from 'react';
import { SessionProvider } from './_providers/SessionContext';
import { OfflineSyncProvider } from './_providers/OfflineSyncContext';
import { AppNav } from './_components/AppNav';

export const metadata = {
  title: 'Meal Planner',
  description: 'AI-assisted household meal planning',
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          <OfflineSyncProvider>
            <AppNav />
            <main>{children}</main>
          </OfflineSyncProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
