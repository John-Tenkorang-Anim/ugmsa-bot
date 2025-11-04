# UGMSA Bot Deployment Guide

This guide will help you deploy the UGMSA AI Bot to various hosting platforms.

## Prerequisites

- Python 3.11 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key

## Environment Variables

Set these environment variables on your hosting platform:

```bash
TELEGRAM_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
PORT=8080  # Optional, defaults to 8080
```

## Deployment Options

### Option 1: Deploy to Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) and create an account
3. Click "New +" and select "Web Service"
4. Connect your GitHub repository
5. Render will automatically detect the `render.yaml` file
6. Set your environment variables in the Render dashboard:
   - `TELEGRAM_TOKEN`
   - `OPENAI_API_KEY`
7. Click "Create Web Service"

The bot will automatically deploy and start running!

### Option 2: Deploy to Heroku

1. Install the Heroku CLI
2. Login to Heroku:
   ```bash
   heroku login
   ```
3. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```
4. Set environment variables:
   ```bash
   heroku config:set TELEGRAM_TOKEN=your_telegram_token
   heroku config:set OPENAI_API_KEY=your_openai_api_key
   ```
5. Deploy:
   ```bash
   git push heroku main
   ```

### Option 3: Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Create a new project
3. Connect your GitHub repository
4. Set environment variables in Railway dashboard
5. Deploy automatically

### Option 4: Deploy to any VPS (DigitalOcean, AWS, etc.)

1. SSH into your server
2. Clone the repository:
   ```bash
   git clone your-repo-url
   cd ugmsa-bot
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your credentials:
   ```bash
   TELEGRAM_TOKEN=your_telegram_token
   OPENAI_API_KEY=your_openai_api_key
   ```
5. Run with a process manager like `pm2` or `systemd`:
   ```bash
   # Using nohup
   nohup python bot.py &

   # Or using screen
   screen -S ugmsa-bot
   python bot.py
   # Press Ctrl+A then D to detach
   ```

## Health Check

The bot includes a health check endpoint that responds to HTTP requests on:
- `http://your-domain:8080/health`
- `http://your-domain:8080/healthz`
- `http://your-domain:8080/`

This is useful for hosting platforms that require health checks.

## Monitoring

The bot uses Python's logging module and outputs logs to stdout. You can monitor logs through your hosting platform's dashboard:

- **Render**: View logs in the "Logs" tab
- **Heroku**: `heroku logs --tail`
- **Railway**: View logs in the deployment dashboard
- **VPS**: Check the output where you ran the bot

## Features

✅ Graceful shutdown handling (SIGTERM, SIGINT)
✅ Health check endpoint for hosting platforms
✅ Proper logging with timestamps
✅ Error recovery and retry logic
✅ Environment variable validation
✅ Async/await for optimal performance

## Troubleshooting

### Bot not responding
- Check that environment variables are set correctly
- Verify your Telegram token is valid
- Check logs for error messages

### Health check failing
- Ensure PORT environment variable is set (default: 8080)
- Check if the port is accessible from the internet

### Knowledge base not loading
- Verify internet connection from your hosting platform
- Check if Google Docs and ugmsa.org are accessible
- Review logs for specific error messages

## Updating the Bot

To update your deployed bot:

1. Make changes to your code
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update bot"
   git push
   ```
3. Most platforms will auto-deploy on push
4. For manual deployments, redeploy through your platform's dashboard

## Support

For issues or questions:
- Check the logs first
- Review environment variables
- Ensure all dependencies are installed
- Verify API keys are valid and have sufficient credits
