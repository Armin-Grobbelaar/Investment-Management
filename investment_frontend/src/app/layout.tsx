import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Investments from "./Investments/page";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Investify",
  description: "See all investments in one place",
};

import SideMenyDrawer from "./Reusable Components/Drawers/SideMenyDrawer";
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
          <SideMenyDrawer />
          {children}
      </body>
    </html>
  );
}

