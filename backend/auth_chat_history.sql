-- ============================================================
-- CHAT HISTORY TABLES FOR GITSIGHT
-- Run this in Supabase SQL Editor
-- ============================================================

-- Chat sessions table (one per conversation)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    repo_url TEXT NOT NULL,
    title TEXT DEFAULT 'New Chat',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat messages table (messages within a session)
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'ai', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS chat_sessions_user_id_idx ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS chat_sessions_repo_url_idx ON chat_sessions(repo_url);
CREATE INDEX IF NOT EXISTS chat_messages_session_id_idx ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS chat_messages_created_at_idx ON chat_messages(created_at);

-- Enable Row Level Security
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for chat_sessions
DROP POLICY IF EXISTS "Users can view own sessions" ON chat_sessions;
CREATE POLICY "Users can view own sessions" ON chat_sessions
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own sessions" ON chat_sessions;
CREATE POLICY "Users can insert own sessions" ON chat_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own sessions" ON chat_sessions;
CREATE POLICY "Users can update own sessions" ON chat_sessions
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own sessions" ON chat_sessions;
CREATE POLICY "Users can delete own sessions" ON chat_sessions
    FOR DELETE USING (auth.uid() = user_id);

-- RLS Policies for chat_messages
DROP POLICY IF EXISTS "Users can view own messages" ON chat_messages;
CREATE POLICY "Users can view own messages" ON chat_messages
    FOR SELECT USING (
        session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can insert own messages" ON chat_messages;
CREATE POLICY "Users can insert own messages" ON chat_messages
    FOR INSERT WITH CHECK (
        session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid())
    );

DROP POLICY IF EXISTS "Users can delete own messages" ON chat_messages;
CREATE POLICY "Users can delete own messages" ON chat_messages
    FOR DELETE USING (
        session_id IN (SELECT id FROM chat_sessions WHERE user_id = auth.uid())
    );

-- Trigger to update updated_at on chat_sessions
CREATE OR REPLACE FUNCTION update_chat_session_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;
CREATE TRIGGER update_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_session_updated_at();

-- Verify setup
SELECT 'Chat history tables created successfully!' as status;
