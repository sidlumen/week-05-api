1. What is the difference between the system prompt and the user message?
Why does the separation matter?
I think system prompt means I give the application a more accurate instructions to work, whereas the user message does not have more control.

2. What happened when you changed the system prompt in Part 4?
What surprised you most?
when I change, I think the tool have more personality. That supprised me I am like talking with a person.
3. Name one situation where using AI in an app could cause harm,
and how you would mitigate it.
I feel like it would make the creation more complecated, and it even make the running crash. I have experienced this. 

4. If you had infinite Claude API credits, what AI feature would you add to this book tracker? Describe it technically.
I would add a more detailed book analyze in it. I think that would require more detailed system prompt.

Lab 6
1. What is the key difference between calling an LLM once and using an agent?
Use an example from today's lab. While using agent, it can slove milti-steps problems. For example, we ask more than one question in Test 3, and the AI agent answer successfully.

2. The agent receives tool results back as "user" role messages. Why does this work?
What does it tell you about how LLMs handle context?
It is about the agent loop. the agent got meessage and then choose tool to use. while tool come up the result, it send the result back to agent. Then agent can end_turn to reply user.

3. What would happen if your tool descriptions were vague or incorrect?
Give a specific example of how bad descriptions could cause wrong behavior.
Bad description would make agent use more token and cause function inefficiently.

4. You now use Claude Code every day. Describe its behavior in terms of what you
learned today: what tools does it likely have? How is the agent loop running?
I understand that when Claude Code thinking - That is when it choosing tools to slove the problem and tool send result back to Claude. I think Claude has thousands of tools. Maybe it is countless.

5. What could go wrong if an agent had the ability to DELETE books and
there was no human-in-the-loop check?
They would make wrong decisions and delete books that people don't want to delete.