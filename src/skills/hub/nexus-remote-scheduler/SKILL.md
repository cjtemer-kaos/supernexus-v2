---
name: nexus-remote-scheduler
description: "A skill that enables remote control via Telegram and handles scheduled background tasks (Cron jobs) for autonomous monitoring and reporting."
category: infrastructure
risk: medium
source: autopsy-jarvis-hrz
tags: "[telegram, scheduler, cron, remote-control, monitoring]"
date_added: "2026-05-08"
---

# nexus-remote-scheduler

## Overview

Inspired by the JARVIS-HRZ autopsy, this skill provides Nexus with a remote communication layer and an autonomous execution schedule. It allows the user to command the system from anywhere via Telegram and ensures that critical tasks (monitoring, research, reporting) happen periodically without manual intervention.

## Core Features

### 1. Telegram Remote Control
- **Command Routing:** Receive and parse commands from a Telegram Bot.
- **Status Updates:** Send real-time notifications about task progress or system health.
- **Asset Delivery:** Receive generated images, videos, or documents directly on your phone.

### 2. Autonomous Scheduler (Cron)
- **Periodic Checks:** Schedule web searches, social media monitoring, or project status updates.
- **Reporting Jobs:** Automatically generate and send reports at specified intervals.
- **Maintenance:** Run cleanup or optimization scripts on a schedule.

## Implementation Details

### Configuration (env)
- `TELEGRAM_BOT_TOKEN`: The API token from BotFather.
- `TELEGRAM_CHAT_ID`: The ID of the authorized user.

### Tooling
- `schedule_task(job_name, interval, command)`: Register a new periodic task.
- `list_scheduled_tasks()`: View active Cron jobs.
- `send_telegram_message(message, chat_id)`: Send a message to the user.
- `receive_telegram_command()`: (Polling/Webhook) Interface for incoming commands.

## Best Practices
- **Security:** Only respond to the authorized `TELEGRAM_CHAT_ID`.
- **Throttling:** Avoid excessive messaging or high-frequency polling.
- **Persistence:** Ensure the scheduler state is saved in `05_MEMORY`.

## Related Skills
- `@agentic-web-orchestrator` - Use for scheduled web monitoring.
- `@nexus-status` - Report health via Telegram.
