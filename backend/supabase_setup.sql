-- ============================================================
-- SUPABASE SQL SETUP FOR GITHUB RAG ASSISTANT
-- LlamaIndex + OpenAI Embeddings + Hybrid Search
-- ============================================================
-- Run this script in Supabase SQL Editor
-- ============================================================

-- Step 1: Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Step 2: Drop existing table and functions (REQUIRED for clean migration)
-- This will delete all existing data - you'll need to re-ingest repositories
DROP TABLE IF EXISTS documents CASCADE;
DROP FUNCTION IF EXISTS match_documents CASCADE;
DROP FUNCTION IF EXISTS hybrid_search CASCADE;
DROP FUNCTION IF EXISTS delete_repo_documents CASCADE;
DROP FUNCTION IF EXISTS check_repo_exists CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;

-- Step 3: Create the new documents table with OpenAI embedding dimensions (1536)
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    repo_url TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    user_id TEXT DEFAULT 'default',
    file_type TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 4: Create indexes for better performance
CREATE INDEX documents_embedding_idx 
ON documents 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX documents_repo_url_idx 
ON documents (repo_url);

CREATE INDEX documents_user_id_idx 
ON documents (user_id);

CREATE INDEX documents_content_trgm_idx 
ON documents 
USING gin (content gin_trgm_ops);

CREATE INDEX documents_repo_user_idx 
ON documents (repo_url, user_id);

-- Step 5: Create vector similarity search function
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_repo_url TEXT,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 10
)
RETURNS TABLE(
    id BIGINT,
    repo_url TEXT,
    file_path TEXT,
    content TEXT,
    metadata JSONB,
    file_type TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.repo_url,
        d.file_path,
        d.content,
        d.metadata,
        d.file_type,
        (1 - (d.embedding <=> query_embedding))::FLOAT as similarity
    FROM documents d
    WHERE d.repo_url = match_repo_url
    AND (1 - (d.embedding <=> query_embedding)) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Step 6: Create hybrid search function
CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1536),
    query_text TEXT,
    match_repo_url TEXT,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 10,
    vector_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE(
    id BIGINT,
    repo_url TEXT,
    file_path TEXT,
    content TEXT,
    metadata JSONB,
    file_type TEXT,
    similarity FLOAT,
    text_rank FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.repo_url,
        d.file_path,
        d.content,
        d.metadata,
        d.file_type,
        (1 - (d.embedding <=> query_embedding))::FLOAT as similarity,
        similarity(d.content, query_text)::FLOAT as text_rank,
        (
            vector_weight * (1 - (d.embedding <=> query_embedding)) +
            (1 - vector_weight) * similarity(d.content, query_text)
        )::FLOAT as combined_score
    FROM documents d
    WHERE d.repo_url = match_repo_url
    AND (
        (1 - (d.embedding <=> query_embedding)) > match_threshold
        OR similarity(d.content, query_text) > 0.1
    )
    ORDER BY combined_score DESC
    LIMIT match_count;
END;
$$;

-- Step 7: Create helper functions
CREATE OR REPLACE FUNCTION delete_repo_documents(target_repo_url TEXT)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INT;
BEGIN
    WITH deleted AS (
        DELETE FROM documents
        WHERE repo_url = target_repo_url
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    RETURN deleted_count;
END;
$$;

CREATE OR REPLACE FUNCTION check_repo_exists(target_repo_url TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN EXISTS(SELECT 1 FROM documents WHERE repo_url = target_repo_url LIMIT 1);
END;
$$;

-- Step 8: Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Step 9: Verify setup
SELECT 'Setup complete!' as status;
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'documents';
