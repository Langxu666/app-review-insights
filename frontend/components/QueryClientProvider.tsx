"use client";

import { QueryClient, QueryClientProvider as ReactQueryProvider } from "@tanstack/react-query";
import { useState } from "react";

export default function QueryClientProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(() =>
    new QueryClient({
      defaultOptions: {
        queries: {
          retry: 1,
          refetchOnWindowFocus: false,
        },
      },
    })
  );

  return <ReactQueryProvider client={queryClient}>{children}</ReactQueryProvider>;
}