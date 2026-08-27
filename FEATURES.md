Your architecture can support both of those capabilities, but there are important distinctions between what Telegram allows and what your bot application has to implement.
1. Anonymous user → bot
A user sends something to the bot, and Telegram delivers the resulting Update to your single webhook:
Telegram
   │
   │ POST /webhook
   ▼
┌─────────────────────────┐
│ Webhook / Validation    │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Update Router           │
│ message / callback / …  │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Support / Automation /  │
│ Moderation / Other       │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ Telegram Bot API        │
└─────────────────────────┘
The bot can respond without revealing the user's identity to another participant, depending on the workflow.
For example:
User
  ↓
"Hello, I need help"
  ↓
Bot
  ↓
Create anonymous support ticket #1842
  ↓
Agent receives:
"New anonymous request #1842:
Hello, I need help"
The crucial point is that Telegram still provides the bot with the sender information in the incoming Update. "Anonymous" is therefore an application-level privacy feature: your bot can deliberately avoid exposing the sender's identity to the recipient/agent, while retaining the necessary internal identifier for conversation state and replies.
2. Bot can update existing content
Yes.
Once the bot has a message ID and chat ID, it can use Telegram Bot API methods such as:
editMessageText
editMessageCaption
editMessageReplyMarkup
deleteMessage
sendMessage
For example:
Original post
┌──────────────────────────────┐
│ Product announcement         │
│                              │
│ [Visit website]              │
└──────────────────────────────┘
              │
              ▼
Application changes content
              │
              ▼
editMessageText(...)
editMessageReplyMarkup(...)
              │
              ▼
Updated post
┌──────────────────────────────┐
│ Updated announcement         │
│ New information here         │
│                              │
│ [Visit website]              │
└──────────────────────────────┘
Your state storage should therefore keep identifiers such as:
chat_id
message_id
content_id
version
created_at
updated_at
That allows your application to locate and modify previously published messages.
3. Bot can add or change an inline URL button
Yes.
An inline keyboard is simply part of the message's reply markup.
Conceptually:
{
  "inline_keyboard": [
    [
      {
        "text": "Open Website",
        "url": "https://example.com"
      }
    ]
  ]
}
The application can initially publish:
[Open Website]
and later replace it with:
[Open Updated Page]
without necessarily replacing the entire message.
That is handled through:
editMessageReplyMarkup
So your architecture can support a workflow such as:
Admin
  ↓
Change URL in configuration
  ↓
State Storage
  ↓
Find all affected message IDs
  ↓
Telegram Bot API
  ↓
editMessageReplyMarkup
  ↓
Existing Telegram posts now point to the new URL
4. "Anytime" has a technical qualification
The bot can initiate an outbound API operation whenever your application is running and has the necessary identifiers/permissions.
That means it does not have to wait for a new user message.
For example:
09:00
Scheduler
   ↓
Check database
   ↓
URL changed?
   ↓ yes
Find published messages
   ↓
Telegram API
   ↓
Update buttons
This is where your cron/scheduler component becomes useful.
Your system can therefore have two independent flows:
INBOUND

Telegram
   ↓
Webhook
   ↓
Validation
   ↓
Router
   ↓
Module
   ↓
State
and:
OUTBOUND / PROACTIVE

Scheduler / Admin Action / Automation
   ↓
Module
   ↓
State
   ↓
Telegram Bot API
   ↓
send / edit / delete / callback / chat management
The webhook is the single inbound endpoint. It does not mean that every bot action must originate from a webhook request.
5. Your complete architecture
For the bot you are describing, I would model it as:
┌──────────────────────┐
                       │      Telegram        │
                       └──────────┬───────────┘
                                  │
                         Incoming Update
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   SINGLE WEBHOOK     │
                       │      /webhook        │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │      VALIDATION      │
                       │ secret / JSON /      │
                       │ request validation   │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   UPDATE ROUTER      │
                       └──────────┬───────────┘
                                  │
             ┌────────────────────┼───────────────────┐
             ▼                    ▼                   ▼
        message            callback_query       join request
             │                    │                   │
             ▼                    ▼                   ▼
       Support           Interactive UI        Moderation
       Publishing        Automation             Membership
       Moderation
             │                    │                   │
             └────────────────────┼───────────────────┘
                                  ▼
                       ┌──────────────────────┐
                       │    STATE STORAGE    │
                       │ users / tickets /   │
                       │ posts / URLs / jobs │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │   TELEGRAM BOT API  │
                       │ send / edit / delete│
                       │ keyboards / chats   │
                       └──────────────────────┘
                                  ▲
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
               Admin actions               Scheduler
                    │                           │
                    └─────────────┬─────────────┘
                                  │
                              proactive
                              updates
So the answer to your two requirements is yes:
Anonymous interaction: yes, through an application-level anonymous support/proxy workflow.
Update content later: yes, provided the bot has the relevant chat_id/message_id and Telegram permits the operation.
Change/add URL inline buttons later: yes, using Telegram's inline keyboard and message-reply-markup editing APIs.
Do this without a new incoming message: yes. Your scheduler, admin endpoint, queue, or internal automation can trigger the Bot API directly.
The one thing I would change in the earlier description is the wording "the application is responsible for processing each received update internally." That is correct for inbound events, but the architecture should explicitly distinguish inbound webhook processing from proactive outbound operations. That distinction matters for the content-update and scheduled-URL functionality you want.
