# Implement AI agent for Live Message Triage

## Context

This repo is a created for testingI have added a commit "Milestone: Before Hackathon". This include all work I have done before the actual hackathon. I tried to set up a bot.

What I did in hackathon:

- Limitation and walk-around
- 1. Bot is blocked by company network. But "Webex Integration" is working. So the messahe is relied to integration. Another issue is the integration will not trigger notification. A temporary walkaround is in the python function that rely message, also programmatically send a message/notification to MS_OS
  2. Since the python server is running locally and we are not able to expose the localhost to public url. So we did not use webhook. I used polling. It pulls every 500ms from webex and save the message to db.
- I setup a message rely channel that can rely received message through integration.
- After that, I add a python funtion that use rule to filter. It is vibe-coded so i don't know how specifically it is implemented. But in our demo we can filter message rely using some rules.
- During the hackathon, my coworker add a LLM. So in the integration chat interface, user can reply in the chat, and the message is sent/captured by our python sever and is treated as "query". Our goal is to allow user to use the Webex integratin to chat with our AI, and it can serve as the user's Webex Assistant. User can use it to:
  - Ask for summary
  - Check current rule
  - Set new focus rule
  - Turn the focus mode on and off
- However, the actualy function/tools are not available yet. We just briefly talked about it during the hackathon demo.

## Next Steps / Vision

- I need to implement the actual AI feature.
- Also, i need to add a UI (web-based application). it has several tabs (maybe toggled from side), so user can open a chat interface, which is the exact copy of the Webex interface. Maybe the UI is fancier. The other tab will be triage management, so user can review messages over the day, and review the triage result. The other tab is to manage the rule applied. Other tab can be the list of daily summary
- For the non-Chat feature, I don't yet now what to be displayed and supported. Some idea:
  - user can check if the grouped/catorized chat is accurata and can mark
  - So far, i just want to support two categories (for simplicity) -- High Priority (notify user); Regular (not notifiing).
- The summarization is a tool available in the AI, user can ask for summary all the time. In addition, summary will be auto generated when 1) focus mode is turned off, and 2) at the end of the day (11:59pm) --- the end-of-day summary will be emailed by the user.

## To-Do

Help me re-vision and restructure this playaround project. Break the new project into phases as well.

Assume i have access to OpenAI API, but i might also use Claude's API.

To all response, the response should be supported by template. So later my coworker (non-technical background) can update it to imporve the user exapreince.

Note
