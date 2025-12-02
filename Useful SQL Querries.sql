SELECT id, agent_name, memory_text, timestamp
FROM agent_memory
WHERE agent_name = 'Perry'  Replace 'Perry' with Netty, Netty P, or Moderator.
ORDER BY timestamp DESC;

Show the Last 5 Memories for an Agent
SELECT id, memory_text, timestamp
FROM agent_memory
WHERE agent_name = 'Netty'
ORDER BY timestamp DESC
LIMIT 5;

Clear All Memories for an Agent
DELETE FROM agent_memory
WHERE agent_name = 'Netty P';  Replace 'Perry' with Netty, Netty P, or Moderator.

Clear All Memories (Reset Everything)
TRUNCATE TABLE agent_memory;

Count Memories per Agent
SELECT agent_name, COUNT(*) AS memory_count
FROM agent_memory
GROUP BY agent_name;

Search Memories by Keyword
SELECT id, agent_name, memory_text, timestamp
FROM agent_memory
WHERE memory_text LIKE '%spaceship%'
ORDER BY timestamp DESC;

