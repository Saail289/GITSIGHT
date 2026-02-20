"""
GitHub scraper service for fetching repository content.
Downloads README, documentation, and code files from GitHub repos.
Uses Git Trees API + PARALLEL fetching for MAXIMUM speed.
"""

import asyncio
import aiohttp
import base64
from github import Github, GithubException
from typing import List, Dict, Any, Optional
from app.config.settings import settings


class GitHubScraper:
    """Service for scraping GitHub repositories with ultra-fast parallel fetching"""
    
    def __init__(self):
        """Initialize GitHub client"""
        self.token = settings.GITHUB_TOKEN
        if self.token:
            self.client = Github(self.token)
        else:
            self.client = Github()  # Unauthenticated (60 requests/hour)
        
        # Supported file extensions
        self.code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs',
            '.html', '.htm', '.css', '.scss', '.sass', '.less',
            '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php',
            '.json', '.yaml', '.yml', '.toml', '.xml', '.ini', '.cfg',
            '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
            '.swift', '.kt', '.scala', '.lua', '.r', '.R', '.sql',
            '.txt', '.rst', '.tex', '.md',
        }
        
        # Directories to skip
        self.skip_dirs = {'node_modules', '.git', 'dist', 'build', '__pycache__', 
                         'venv', '.venv', 'vendor', '.idea', '.vscode'}
    
    def parse_github_url(self, url: str) -> tuple:
        """Parse GitHub URL to extract owner and repo name."""
        url = url.rstrip('/').rstrip('.git')
        if 'github.com/' in url:
            parts = url.split('github.com/')[-1].split('/')
            if len(parts) >= 2:
                return parts[0], parts[1]
        raise ValueError(f"Invalid GitHub URL format: {url}")
    
    def fetch_repository_content(self, repo_url: str) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Fetch all relevant content from a GitHub repository using Git Trees API.
        This is MUCH faster than fetching files one by one.
        """
        try:
            owner, repo_name = self.parse_github_url(repo_url)
            repo = self.client.get_repo(f"{owner}/{repo_name}")
            
            # Get default branch
            default_branch = repo.default_branch
            print(f"Fetching tree for branch: {default_branch}")
            
            # Get full tree in ONE API call (recursive=True gets everything!)
            tree = repo.get_git_tree(default_branch, recursive=True)
            
            # Collect all file paths and files to fetch
            all_file_paths = []
            files_to_fetch = []
            
            for item in tree.tree:
                if item.type == "blob":  # It's a file
                    path = item.path
                    
                    # Skip files in excluded directories
                    if any(skip_dir in path.split('/') for skip_dir in self.skip_dirs):
                        continue
                    
                    all_file_paths.append(path)
                    
                    # Check if it's a supported file type
                    ext = '.' + path.split('.')[-1] if '.' in path else ''
                    if ext.lower() in self.code_extensions:
                        # Skip large files (>100KB)
                        if item.size and item.size < 100000:
                            files_to_fetch.append({
                                'path': path,
                                'sha': item.sha,
                                'size': item.size,
                                'repo_url': repo_url
                            })
            
            print(f"Found {len(all_file_paths)} total files, fetching {len(files_to_fetch)} code files...")
            
            # Fetch all file contents in parallel using blob API
            # When inside FastAPI's event loop, run async code in a separate thread
            try:
                asyncio.get_running_loop()
                # We're inside an existing event loop (FastAPI/Uvicorn)
                # Run the async function in a new thread with its own event loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._parallel_fetch_blobs(files_to_fetch, owner, repo_name)
                    )
                    documents = future.result()
            except RuntimeError:
                # No running event loop, safe to use asyncio.run() directly
                documents = asyncio.run(
                    self._parallel_fetch_blobs(files_to_fetch, owner, repo_name)
                )
            
            # Add README at the beginning if exists
            readme_doc = self._fetch_readme(repo, repo_url)
            if readme_doc:
                # Remove duplicate README if already fetched
                documents = [d for d in documents if d['file_path'].lower() != 'readme.md']
                documents.insert(0, readme_doc)
            
            return documents, sorted(all_file_paths)
            
        except GithubException as e:
            raise Exception(f"GitHub API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error fetching repository: {str(e)}")
    
    async def _fetch_single_blob(self, session: aiohttp.ClientSession, file_info: Dict, 
                                  owner: str, repo_name: str) -> Optional[Dict]:
        """Fetch a single file's content via GitHub Blob API (async)"""
        sha = file_info['sha']
        path = file_info['path']
        
        # Use blob endpoint - more efficient than contents endpoint
        url = f"https://api.github.com/repos/{owner}/{repo_name}/git/blobs/{sha}"
        
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-RAG-Assistant'
        }
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Decode base64 content
                    content = base64.b64decode(data['content']).decode('utf-8')
                    
                    print(f"  ✓ {path}")
                    return {
                        'repo_url': file_info['repo_url'],
                        'file_path': path,
                        'content': content,
                        'metadata': {
                            'type': 'code',
                            'language': path.split('.')[-1] if '.' in path else 'text',
                            'size': file_info['size']
                        }
                    }
                else:
                    print(f"  ✗ {path}: HTTP {response.status}")
                    return None
        except Exception as e:
            print(f"  ✗ {path}: {e}")
            return None
    
    async def _parallel_fetch_blobs(self, files_to_fetch: List[Dict], 
                                     owner: str, repo_name: str) -> List[Dict]:
        """Fetch all file contents in parallel using blob API"""
        documents = []
        
        # Option B: Git Trees API with standard 10 concurrent connections
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=120)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create tasks for all files
            tasks = [
                self._fetch_single_blob(session, file_info, owner, repo_name)
                for file_info in files_to_fetch
            ]
            
            # Execute all tasks in parallel
            print(f"Parallel fetching {len(tasks)} files with 10 concurrent connections...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect successful results
            for result in results:
                if isinstance(result, dict) and result is not None:
                    documents.append(result)
        
        print(f"Successfully fetched {len(documents)} files")
        return documents
    
    def _fetch_readme(self, repo, repo_url: str) -> Optional[Dict[str, Any]]:
        """Fetch README file"""
        try:
            readme = repo.get_readme()
            content = base64.b64decode(readme.content).decode('utf-8')
            
            return {
                'repo_url': repo_url,
                'file_path': 'README.md',
                'content': content,
                'metadata': {
                    'type': 'readme',
                    'size': readme.size
                }
            }
        except:
            return None