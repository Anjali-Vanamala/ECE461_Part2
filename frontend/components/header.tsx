"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Package2, Menu, X, Sun, Moon, Settings2 } from "lucide-react"
import { useState } from "react"
import { useTheme } from "@/providers/theme-provider"

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { theme, setTheme } = useTheme()

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary">
            <Package2 className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-lg font-bold">Model Registry</span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden gap-6 md:flex">
          <Link href="/browse" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Browse
          </Link>
          <Link href="/health" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Health
          </Link>
          <Link href="/docs" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            API Docs
          </Link>
        </nav>

        <div className="hidden gap-3 md:flex items-center">
          <div className="flex items-center gap-1">
            <button
              onClick={() => setTheme("light")}
              className={`p-2 rounded-md transition-colors ${
                theme === "light"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
              aria-label="Light theme"
              title="Light"
            >
              <Sun className="h-4 w-4" />
            </button>
            <button
              onClick={() => setTheme("dark")}
              className={`p-2 rounded-md transition-colors ${
                theme === "dark"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
              aria-label="Dark theme"
              title="Dark"
            >
              <Moon className="h-4 w-4" />
            </button>
            <button
              onClick={() => setTheme("system")}
              className={`p-2 rounded-md transition-colors ${
                theme === "system"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
              aria-label="System theme"
              title="System"
            >
              <Settings2 className="h-4 w-4" />
            </button>
          </div>

          <Button variant="outline" size="sm" asChild>
            <Link href="/upload">Upload</Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/ingest">Ingest</Link>
          </Button>
        </div>

        {/* Mobile Menu Button */}
        <button className="md:hidden" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} aria-label="Toggle menu">
          {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="border-t border-border bg-card md:hidden">
          <nav className="flex flex-col gap-3 px-4 py-4">
            <Link href="/browse" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Browse
            </Link>
            <Link href="/health" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              Health
            </Link>
            <Link href="/docs" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              API Docs
            </Link>
            <div className="flex items-center gap-1 border-t border-border pt-3 mt-2">
              <span className="text-xs text-muted-foreground px-2">Theme:</span>
              <button
                onClick={() => setTheme("light")}
                className={`p-1.5 rounded transition-colors ${
                  theme === "light"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
                aria-label="Light theme"
              >
                <Sun className="h-4 w-4" />
              </button>
              <button
                onClick={() => setTheme("dark")}
                className={`p-1.5 rounded transition-colors ${
                  theme === "dark"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
                aria-label="Dark theme"
              >
                <Moon className="h-4 w-4" />
              </button>
              <button
                onClick={() => setTheme("system")}
                className={`p-1.5 rounded transition-colors ${
                  theme === "system"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
                aria-label="System theme"
              >
                <Settings2 className="h-4 w-4" />
              </button>
            </div>

            <Button variant="outline" size="sm" asChild className="w-full justify-center bg-transparent">
              <Link href="/upload">Upload</Link>
            </Button>
            <Button size="sm" asChild className="w-full justify-center">
              <Link href="/ingest">Ingest</Link>
            </Button>
          </nav>
        </div>
      )}
    </header>
  )
}
