import type { ReactNode } from "react";
import { dir } from "@/lib/i18n";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fa" dir={dir("fa")}>
      <body style={{ marginInline: "auto", maxInlineSize: 720, paddingInline: 16 }}>{children}</body>
    </html>
  );
}
