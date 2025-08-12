# Exam Grader - Vercel Deployment Script (PowerShell)

Write-Host "🚀 Starting Vercel deployment for Exam Grader..." -ForegroundColor Green

# Check if Vercel CLI is installed
try {
    vercel --version | Out-Null
    Write-Host "✅ Vercel CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ Vercel CLI not found. Installing..." -ForegroundColor Red
    npm install -g vercel
}

# Build CSS assets
Write-Host "🎨 Building CSS assets..." -ForegroundColor Yellow
npm run build-css-prod

# Check if user is logged in to Vercel
Write-Host "🔐 Checking Vercel authentication..." -ForegroundColor Yellow
try {
    vercel whoami | Out-Null
    Write-Host "✅ Already logged in to Vercel" -ForegroundColor Green
} catch {
    Write-Host "Please log in to Vercel:" -ForegroundColor Yellow
    vercel login
}

# Deploy to Vercel
Write-Host "📦 Deploying to Vercel..." -ForegroundColor Yellow
vercel --prod

Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Set up environment variables if not already done:" -ForegroundColor White
Write-Host "   vercel env add OPENAI_API_KEY" -ForegroundColor Gray
Write-Host "   vercel env add HANDWRITING_OCR_API_KEY" -ForegroundColor Gray
Write-Host "   vercel env add SECRET_KEY" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Check your deployment:" -ForegroundColor White
Write-Host "   vercel logs" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Test the health endpoint:" -ForegroundColor White
Write-Host "   Invoke-WebRequest https://your-app.vercel.app/api/health" -ForegroundColor Gray