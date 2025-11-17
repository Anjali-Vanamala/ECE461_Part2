"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useState } from "react"
import { Upload, File, AlertCircle } from "lucide-react"

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [modelName, setModelName] = useState("")
  const [description, setDescription] = useState("")

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0])
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto">
          <h1 className="text-3xl font-bold text-foreground mb-2">Upload Model</h1>
          <p className="text-muted-foreground mb-8">Upload your custom ML model to the registry</p>

          <div className="grid gap-6">
            {/* Upload Area */}
            <Card className="bg-card/40 border-border/50 backdrop-blur border-2 border-dashed p-8 text-center cursor-pointer hover:border-primary/50 transition-colors">
              <input
                type="file"
                id="file-upload"
                className="hidden"
                onChange={handleFileChange}
                accept=".zip,.tar,.gz"
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                {file ? (
                  <div className="space-y-3">
                    <File className="h-10 w-10 mx-auto text-primary" />
                    <div>
                      <p className="font-semibold text-foreground">{file.name}</p>
                      <p className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Upload className="h-10 w-10 mx-auto text-muted-foreground" />
                    <div>
                      <p className="font-semibold text-foreground">Click to upload or drag and drop</p>
                      <p className="text-xs text-muted-foreground">ZIP, TAR, or GZ files up to 5GB</p>
                    </div>
                  </div>
                )}
              </label>
            </Card>

            {/* Form Fields */}
            <Card className="bg-card/40 border-border/50 backdrop-blur p-6 space-y-6">
              <div>
                <label htmlFor="model-name" className="block text-sm font-medium text-foreground mb-2">
                  Model Name
                </label>
                <Input
                  id="model-name"
                  placeholder="e.g., BERT Fine-tuned for Sentiment"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                />
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-foreground mb-2">
                  Description
                </label>
                <textarea
                  id="description"
                  placeholder="Describe your model, its capabilities, and intended use..."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  rows={5}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div className="rounded-lg bg-secondary/10 border border-secondary/20 p-4 flex gap-3">
                <AlertCircle className="h-5 w-5 text-secondary flex-shrink-0 mt-0.5" />
                <div className="text-sm text-muted-foreground">
                  <p className="font-medium text-foreground mb-1">Privacy Notice</p>
                  <p>
                    Your model will be stored securely and will not be publicly visible unless you mark it as public.
                  </p>
                </div>
              </div>
            </Card>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button className="flex-1" disabled={!file || !modelName}>
                Upload Model
              </Button>
              <Button variant="outline" className="flex-1 bg-transparent">
                Cancel
              </Button>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
