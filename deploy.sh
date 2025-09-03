#!/bin/bash

# Exam Grader - Vercel Deployment Script

echo "🚀 Starting Vercel deployment for Exam Grader..."

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Build CSS assets
echo "🎨 Building CSS assets..."
npm run build-css-prod

# Check if user is logged in to Vercel
echo "🔐 Checking Vercel authentication..."
if ! vercel whoami &> /dev/null; then
    echo "Please log in to Vercel:"
    vercel login
fi

# Deploy to Vercel
echo "📦 Deploying to Vercel..."
vercel --prod

echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set up environment variables if not already done:"
echo "   vercel env add OPENAI_API_KEY"
echo "   vercel env add HANDWRITING_OCR_API_KEY"
echo "   vercel env add SECRET_KEY"
echo ""
echo "2. Check your deployment:"
echo "   vercel logs"
echo ""
echo "3. Test the health endpoint:"
echo "   curl https://your-app.vercel.app/api/health"