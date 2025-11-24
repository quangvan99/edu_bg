# GIAOAN AI - PDF CONTEXT SYSTEM - INCREMENTAL IMPLEMENTATION PLAN

## Overview

Plan implement tính năng upload PDF để làm context cho việc tạo giáo án, chia thành **5 phases** có thể test và demo độc lập từng phase.

## Design Philosophy

- ✅ **Each phase delivers working functionality**
- ✅ **Testing after each phase**
- ✅ **Progressive enhancement**
- ✅ **Rollback possible at any phase**
- ✅ **User feedback integration**

---

## 🟢 PHASE 1: BASIC PDF TEXT EXTRACTION (Week 1-2)

**Goal**: Extract text from PDF/DOCX and save as structured files

### 1.1 Core Components
```python
# core/document_processor.py
class DocumentProcessor:
    """Unified document processor using pypandoc"""
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.doc', '.md', '.txt', '.html']

    def extract_text(self, file_path: str) -> str:
        """Extract text using pypandoc for ALL formats"""
        try:
            import pypandoc
            text = pypandoc.convert_file(file_path, 'plain')
            return self._clean_text(text)
        except Exception as e:
            raise Exception(f"Error processing {file_path}: {e}")

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Fix encoding issues
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        return text.strip()

    def get_file_metadata(self, file_path: str) -> dict:
        """Get file metadata"""
        import os
        from datetime import datetime

        stat = os.stat(file_path)
        return {
            'filename': os.path.basename(file_path),
            'extension': os.path.splitext(file_path)[1].lower(),
            'size_bytes': stat.st_size,
            'created_date': datetime.fromtimestamp(stat.st_ctime),
            'modified_date': datetime.fromtimestamp(stat.st_mtime)
        }
```

### 1.2 Simple CLI Test
```python
# test_document_extraction.py
def test_single_file():
    processor = DocumentProcessor()

    # Test various formats
    test_files = [
        "sample.pdf",
        "document.docx",
        "notes.md",
        "text.txt"
    ]

    for file_path in test_files:
        try:
            text = processor.extract_text(file_path)
            print(f"✅ {file_path}: {len(text)} characters")

            # Save preview
            preview_file = f"preview_{os.path.basename(file_path)}.txt"
            with open(preview_file, 'w', encoding='utf-8') as f:
                f.write(text[:1000] + "..." if len(text) > 1000 else text)

        except Exception as e:
            print(f"❌ {file_path}: {e}")

def test_batch_processing():
    processor = DocumentProcessor()
    documents_dir = "test_documents"

    for file_path in glob.glob(f"{documents_dir}/*"):
        if any(file_path.endswith(ext) for ext in processor.supported_formats):
            process_document(processor, file_path)

def process_document(processor, file_path):
    """Process single document and save to data/processed/"""
    try:
        # Extract text
        text = processor.extract_text(file_path)
        metadata = processor.get_file_metadata(file_path)

        # Save to structured format
        output_dir = "data/processed"
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = f"{output_dir}/{base_name}_extracted.json"

        document_data = {
            'metadata': metadata,
            'content': text,
            'processed_date': datetime.now().isoformat()
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(document_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"✅ Processed: {file_path} → {output_file}")

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
```

### 1.3 Dependencies
```bash
# PyPDF for document processing (supports all formats)
pip install pypandoc

# Additional utilities
pip install rich tqdm

# Pandoc system requirement (install separately):
# Ubuntu/Debian: sudo apt-get install pandoc
# macOS: brew install pandoc
# Windows: Download from https://pandoc.org/installing.html
```

### 1.4 Deliverables ✅
- [ ] `core/document_processor.py` - Unified document processor (pypandoc)
- [ ] `test_document_extraction.py` - Multi-format test script
- [ ] `data/processed/` directory structure with JSON output
- [ ] Working demo: Upload any format → Extract text → Save structured data
- [ ] Test report: Success rate across different file formats

### 1.5 Success Criteria
- ✅ Extract text from 95% of files (PDF, DOCX, MD, TXT) successfully
- ✅ Handle Vietnamese encoding and special characters
- ✅ Process files < 50MB in < 30 seconds
- ✅ Output structured JSON with metadata and content
- ✅ Consistent behavior across all supported formats

---

## 🟡 PHASE 2: SIMPLE TEXT SEARCH & INDEXING (Week 3-4)

**Goal**: Search through extracted text using keyword matching

### 2.1 Core Components
```python
# core/simple_search.py
class SimpleTextSearch:
    def __init__(self, documents_dir: str)
    def index_document(self, doc_id: str, text: str, metadata: dict) -> None
    def search(self, query: str, limit: int = 5) -> List[dict]
    def get_document_snippet(self, doc_id: str, start: int, length: int) -> str

# core/document_manager.py
class DocumentManager:
    def __init__(self, storage_dir: str):
        self.processor = DocumentProcessor()
        self.search = SimpleTextSearch(storage_dir)

    def upload_and_index(self, file_path: str, doc_type: str) -> dict:
        """Process ANY format using pypandoc and index"""
        try:
            # Extract text using pypandoc
            text = self.processor.extract_text(file_path)
            metadata = self.processor.get_file_metadata(file_path)
            metadata['doc_type'] = doc_type

            # Generate document ID
            doc_id = f"{doc_type}_{metadata['filename']}_{int(time.time())}"

            # Index for search
            self.search.index_document(doc_id, text, metadata)

            # Save processed document
            self._save_processed_document(doc_id, file_path, text, metadata)

            return {
                'doc_id': doc_id,
                'filename': metadata['filename'],
                'size_chars': len(text),
                'doc_type': doc_type
            }

        except Exception as e:
            raise Exception(f"Failed to process {file_path}: {e}")

    def _save_processed_document(self, doc_id: str, file_path: str, text: str, metadata: dict):
        """Save processed document as JSON"""
        processed_data = {
            'doc_id': doc_id,
            'original_path': file_path,
            'metadata': metadata,
            'content': text,
            'processed_date': datetime.now().isoformat()
        }

        output_file = f"data/processed/{doc_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2, default=str)
```

### 2.2 Test Integration
```python
# test_search_integration.py
def test_multi_format_search():
    manager = DocumentManager("data/documents")

    # Test different formats
    test_files = [
        ("sgk_toan.pdf", "sgk"),
        ("tailieu_gv.docx", "tailieu_gv"),
        ("ghi_chu.md", "notes"),
        ("bai_tap.txt", "exercises")
    ]

    uploaded_docs = []
    for file_path, doc_type in test_files:
        try:
            doc_info = manager.upload_and_index(file_path, doc_type)
            uploaded_docs.append(doc_info)
            print(f"✅ Uploaded: {file_path} → {doc_info['doc_id']}")
        except Exception as e:
            print(f"❌ Failed to upload {file_path}: {e}")

    # Search across all formats
    search_queries = ["tam giác", "định lý", "bài tập", "hình học"]

    for query in search_queries:
        print(f"\n🔍 Searching for: '{query}'")
        results = manager.search.search(query, limit=3)

        for result in results:
            print(f"  📄 {result['metadata']['filename']} ({result['metadata']['doc_type']})")
            snippet = manager.search.get_document_snippet(
                result['doc_id'], result['start_pos'], 150
            )
            print(f"     {snippet}...")

def test_search_performance():
    """Test search performance with multiple documents"""
    import time

    manager = DocumentManager("data/documents")

    # Upload batch documents
    start_time = time.time()
    for i in range(10):
        test_file = f"test_doc_{i}.pdf"
        manager.upload_and_index(test_file, "test")
    upload_time = time.time() - start_time

    # Test search speed
    start_time = time.time()
    results = manager.search.search("test query")
    search_time = time.time() - start_time

    print(f"Uploaded 10 docs in {upload_time:.2f}s")
    print(f"Search completed in {search_time:.3f}s")
    print(f"Found {len(results)} results")
```

### 2.3 CLI Interface
```python
# cli_search.py
def interactive_search():
    while True:
        query = input("Search query (or 'quit'): ")
        if query == 'quit': break

        results = search_engine.search(query)
        display_results(results)
```

### 2.4 Deliverables ✅
- [ ] `core/simple_search.py` - Keyword search engine
- [ ] `core/document_manager.py` - Document management
- [ ] `cli_search.py` - Interactive search interface
- [ ] `data/documents/` with indexed content
- [ ] Working demo: Upload 3 PDFs → Search → Display snippets

### 2.5 Success Criteria
- ✅ Search through 100+ documents in < 2 seconds
- ✅ Highlight search terms in results
- ✅ Support Vietnamese diacritics in search
- ✅ Basic relevance ranking (frequency, position)

---

## 🟠 PHASE 3: BASIC CONTEXT INTEGRATION (Week 5-6)

**Goal**: Integrate search results into prompt generation

### 3.1 Enhanced Prompt Generator
```python
# prompts/context_prompt_generator.py
class ContextPromptGenerator:
    def __init__(self, search_engine: SimpleTextSearch):
        self.search_engine = search_engine

    def generate_prompt_with_context(
        self,
        original_prompt: str,
        lesson_topic: str,
        max_context_chars: int = 2000
    ) -> str:

        # Search for relevant content
        search_results = self.search_engine.search(lesson_topic, limit=3)

        # Build context
        context = self._build_context(search_results, max_context_chars)

        # Enhanced prompt template
        enhanced_prompt = f"""
{original_prompt}

**THAM KHẢO TÀI LIỆU:**
{context}

**Lưu ý:** Sử dụng thông tin từ tài liệu tham khảo để làm phong phú nội dung.
"""
        return enhanced_prompt
```

### 3.2 Integration with Existing System
```python
# enhanced_run.py
class EnhancedGiaoAn(GiaoAnGenerator):
    def __init__(self):
        super().__init__()
        self.doc_manager = DocumentManager("data/documents")
        self.prompt_gen = ContextPromptGenerator(self.doc_manager.search)

    def process_unit_with_context(self, unit: dict, context: str = ""):
        # Get base prompt
        base_prompt = self.prompt_gen.generate_create_prompt(unit, "")

        # Add context
        enhanced_prompt = self.prompt_gen.generate_prompt_with_context(
            base_prompt,
            self.noi_dung_bai_giang
        )

        # Generate with enhanced prompt
        response = self.ai_client.generate_response(enhanced_prompt)
        return self.extract_markdown(response)
```

### 3.3 Test Framework
```python
# test_context_integration.py
def test_context_enhancement():
    # Setup
    generator = EnhancedGiaoAn()
    generator.doc_manager.upload_and_index("sgk_toan.pdf", "sgk")

    # Test without context
    original_content = generator.process_unit({'title': 'Năng lực'}, "")

    # Test with context
    enhanced_content = generator.process_unit_with_context({'title': 'Năng lực'}, "")

    # Compare results
    compare_results(original_content, enhanced_content)
```

### 3.4 Deliverables ✅
- [ ] `prompts/context_prompt_generator.py` - Context-aware prompts
- [ ] `enhanced_run.py` - Enhanced main system
- [ ] `test_context_integration.py` - Integration tests
- [ ] Demo comparison: With vs Without context
- [ ] Performance metrics report

### 3.5 Success Criteria
- ✅ Generated content includes relevant information from PDFs
- ✅ Response time < 15 seconds (including search)
- ✅ Context length properly managed (< 3000 tokens)
- ✅ Quality improvement measurable (user testing)

---

## 🔵 PHASE 4: VECTOR SEARCH & SEMANTIC MATCHING (Week 7-8)

**Goal**: Implement semantic search using vector embeddings

### 4.1 Vector Storage Implementation
```python
# core/vector_search.py
class VectorSearch:
    def __init__(self, persist_directory: str = "data/vectors"):
        from sentence_transformers import SentenceTransformer
        import chromadb

        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.client = chromadb.PersistentClient(persist_directory)
        self.collection = self.client.get_or_create_collection("documents")

    def add_document(self, doc_id: str, text_chunks: List[str], metadata: dict):
        # Generate embeddings
        embeddings = self.model.encode(text_chunks)

        # Store in vector DB
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=text_chunks,
            metadatas=[metadata] * len(text_chunks),
            ids=[f"{doc_id}_{i}" for i in range(len(text_chunks))]
        )

    def semantic_search(self, query: str, limit: int = 5) -> List[dict]:
        # Generate query embedding
        query_embedding = self.model.encode([query])

        # Search
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=limit
        )

        return self._format_results(results)
```

### 4.2 Enhanced Search Engine
```python
# core/hybrid_search.py
class HybridSearch:
    def __init__(self):
        self.keyword_search = SimpleTextSearch()
        self.vector_search = VectorSearch()

    def search(self, query: str, strategy: str = "hybrid") -> List[dict]:
        if strategy == "keyword":
            return self.keyword_search.search(query)
        elif strategy == "vector":
            return self.vector_search.semantic_search(query)
        else:  # hybrid
            keyword_results = self.keyword_search.search(query, limit=10)
            vector_results = self.vector_search.semantic_search(query, limit=10)
            return self._merge_and_rank(keyword_results, vector_results)
```

### 4.3 Migration Tools
```python
# tools/migrate_to_vectors.py
def migrate_existing_documents():
    """Migrate existing extracted texts to vector storage"""
    doc_manager = DocumentManager("data/documents")
    vector_search = VectorSearch()

    for doc in doc_manager.list_documents():
        # Load extracted text
        text = load_extracted_text(doc['file_path'])

        # Chunk for vector storage
        chunks = chunk_text(text, chunk_size=500)

        # Add to vector store
        vector_search.add_document(doc['id'], chunks, doc['metadata'])

    print("Migration completed!")
```

### 4.4 Deliverables ✅
- [ ] `core/vector_search.py` - Semantic search with ChromaDB
- [ ] `core/hybrid_search.py` - Combined search strategies
- [ ] `tools/migrate_to_vectors.py` - Migration utility
- [ ] Performance comparison: Keyword vs Vector vs Hybrid
- [ ] Search quality metrics

### 4.5 Success Criteria
- ✅ Semantic search finds relevant content even with different keywords
- ✅ Search time < 3 seconds for 1000 documents
- ✅ Vector storage size < 50% of original text size
- ✅ Improved search relevance > 20% over keyword search

---

## 🟣 PHASE 5: PRODUCTION INTEGRATION & OPTIMIZATION (Week 9-10)

**Goal**: Full integration with UI, performance optimization, production ready

### 5.1 Enhanced CLI Interface
```python
# giaoan_plus_pdf.py
class GiaoAnPlusPDF:
    def __init__(self):
        self.generator = EnhancedGiaoAn()
        self.search_engine = HybridSearch()
        self.upload_manager = UploadManager()

    def run_interactive(self):
        while True:
            print("""
=== GIAO AN AI WITH PDF SUPPORT ===
1. Upload new document
2. Manage documents
3. Search documents
4. Create lesson plan (with context)
5. Settings
6. Exit
            """)

            choice = input("Select option: ")

            if choice == "1":
                self.upload_interactive()
            elif choice == "3":
                self.search_interactive()
            elif choice == "4":
                self.create_lesson_plan_with_context()
            # ... other options

    def upload_interactive(self):
        file_path = input("Enter file path: ")
        doc_type = input("Document type (sgk/tailieu/gv/other): ")

        with Progress() as progress:
            task = progress.add_task("Processing...", total=100)

            # Extract text
            progress.update(task, advance=20)
            text = self.pdf_processor.extract_text(file_path)

            # Index
            progress.update(task, advance=40)
            self.search_engine.add_document(file_path, text, {'type': doc_type})

            # Store
            progress.update(task, advance=40)
            self.upload_manager.save_document(file_path, doc_type)

        print("✅ Document uploaded successfully!")

    def create_lesson_plan_with_context(self):
        # Run enhanced lesson plan creation
        pass
```

### 5.2 Performance Optimization
```python
# core/performance_optimizer.py
class PerformanceOptimizer:
    def __init__(self):
        self.cache = {}
        self.batch_size = 32

    def batch_process_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Process embeddings in batches for better performance"""
        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.model.encode(batch)
            embeddings.extend(batch_embeddings)
        return embeddings

    def cache_search_results(self, query_hash: str, results: List[dict]):
        """Cache search results for repeated queries"""
        self.cache[query_hash] = {
            'results': results,
            'timestamp': time.time(),
            'ttl': 3600  # 1 hour
        }
```

### 5.3 Monitoring & Analytics
```python
# analytics/usage_tracker.py
class UsageTracker:
    def __init__(self):
        self.metrics = {
            'uploads': 0,
            'searches': 0,
            'lesson_plans_created': 0,
            'avg_response_time': 0
        }

    def track_upload(self, file_size: float, processing_time: float):
        self.metrics['uploads'] += 1
        # Update other metrics...

    def track_search(self, query: str, response_time: float, result_count: int):
        self.metrics['searches'] += 1
        # Log for analysis...

    def generate_report(self) -> dict:
        return self.metrics
```

### 5.4 Production Configuration
```yaml
# config/production_config.yaml
system:
  max_file_size: 52428800  # 50MB
  max_concurrent_uploads: 3
  cache_ttl: 3600

search:
  default_strategy: "hybrid"
  max_results: 10
  similarity_threshold: 0.7

performance:
  embedding_batch_size: 32
  search_timeout: 5
  max_memory_usage: 2048  # MB

storage:
  vector_store_path: "data/vectors"
  uploads_path: "data/uploads"
  cleanup_threshold: 0.8
```

### 5.5 Final Testing Suite
```python
# tests/integration_test_suite.py
class IntegrationTestSuite:
    def test_complete_workflow(self):
        """Test entire workflow from upload to lesson plan generation"""

        # 1. Upload documents
        docs = [
            ("sgk_toan.pdf", "sgk"),
            ("tailieu_gv.docx", "tailieu_gv")
        ]

        for file_path, doc_type in docs:
            self.upload_manager.upload_and_index(file_path, doc_type)

        # 2. Create lesson plan with context
        lesson_plan = self.generator.create_lesson_plan(
            topic="Tam giác đồng dạng",
            use_context=True
        )

        # 3. Verify quality
        assert len(lesson_plan.sections) > 0
        assert "tam giác" in lesson_plan.content.lower()

        # 4. Performance check
        assert lesson_plan.generation_time < 30

        print("✅ Complete workflow test passed!")
```

### 5.6 Deliverables ✅
- [ ] `giaoan_plus_pdf.py` - Production-ready main application
- [ ] `core/performance_optimizer.py` - Performance optimizations
- [ ] `analytics/usage_tracker.py` - Usage monitoring
- [ ] `config/production_config.yaml` - Production settings
- [ ] `tests/integration_test_suite.py` - Complete test suite
- [ ] User documentation and setup guide
- [ ] Performance benchmark report

### 5.7 Success Criteria
- ✅ Complete workflow: Upload → Search → Generate → Export
- ✅ Handle 100+ documents with < 5GB storage
- ✅ Search response < 3 seconds
- ✅ Lesson plan generation < 30 seconds
- ✅ 95% uptime and error handling

---

## 📊 PROJECT TRACKING

### Milestone Checklist
```markdown
## Phase 1 ✅ Week 1-2
- [ ] PDF text extraction working
- [ ] Basic file upload interface
- [ ] Test with sample documents
- [ ] Performance baseline established

## Phase 2 ✅ Week 3-4
- [ ] Keyword search implemented
- [ ] Document indexing system
- [ ] Search performance optimized
- [ ] User feedback integration

## Phase 3 ✅ Week 5-6
- [ ] Context integration with prompts
- [ ] Enhanced lesson plan generation
- [ ] A/B testing results
- [ ] Quality improvements measured

## Phase 4 ✅ Week 7-8
- [ ] Vector search implementation
- [ ] Semantic matching improvements
- [ ] Migration tools completed
- [ ] Search relevance benchmark

## Phase 5 ✅ Week 9-10
- [ ] Full system integration
- [ ] Production optimization
- [ ] Complete testing suite
- [ ] Documentation and deployment
```

### Risk Mitigation by Phase
- **Phase 1**: Fallback to manual text input if PDF extraction fails
- **Phase 2**: Keep existing system as backup if search fails
- **Phase 3**: Option to disable context if quality degrades
- **Phase 4**: Keep keyword search as fallback option
- **Phase 5**: Rollback机制 for all features

---

## 🚀 GETTING STARTED

### Quick Start with Phase 1
```bash
# Clone and setup
git clone <repo>
cd giaoan
pip install -r requirements_phase1.txt

# Test PDF extraction
python test_pdf_extraction.py

# Upload first document
python upload_test.py --file sample.pdf --type sgk
```

### Progressive Enhancement Path
```
Phase 1 → Basic functionality working
Phase 2 → Add search capabilities
Phase 3 → Enhance AI prompts
Phase 4 → Improve search quality
Phase 5 → Production optimization
```

### Testing Strategy
- **Unit Tests**: Each component independently
- **Integration Tests**: Component interactions
- **User Acceptance Tests**: Real workflow testing
- **Performance Tests**: Load and stress testing
- **Quality Tests**: Output quality evaluation

---

## 📈 SUCCESS METRICS

### Technical Metrics
| Phase | Response Time | Success Rate | Storage Efficiency |
|-------|---------------|--------------|-------------------|
| 1     | < 30s         | > 95%        | N/A               |
| 2     | < 5s          | > 98%        | 100%              |
| 3     | < 20s         | > 95%        | 100%              |
| 4     | < 3s          | > 98%        | < 50%             |
| 5     | < 30s         | > 99%        | < 40%             |

### Quality Metrics
- **Content Relevance**: > 85% relevant information included
- **User Satisfaction**: > 4.5/5 rating on enhanced content
- **Efficiency Improvement**: 40% reduction in manual research time
- **Error Rate**: < 2% generation failures

---

## 📋 DEPENDENCIES SIMPLIFIED

### Required System Dependencies
```bash
# Pandoc (required by pypandoc)
sudo apt-get install pandoc  # Ubuntu/Debian
brew install pandoc          # macOS
# Windows: Download from https://pandoc.org/installing.html
```

### Python Dependencies
```bash
# Core document processing
pip install pypandoc

# Phase 2-3: Search and CLI
pip install rich tqdm

# Phase 4-5: Vector search and AI
pip install sentence-transformers chromadb

# Existing dependencies (already in project)
pip install google-generativeai
```

### Key Benefits of pypandoc Approach
- ✅ **Single dependency** for ALL document formats
- ✅ **Proven technology** - Pandoc handles complex documents reliably
- ✅ **Vietnamese support** - Better encoding handling than specialized libraries
- ✅ **Consistent output** - Same behavior across PDF, DOCX, MD, TXT
- ✅ **Easy maintenance** - No multiple parsing libraries to debug

---

## 🎯 NEXT STEPS

1. **Approve Phase 1** implementation plan
2. **Install Pandoc** system dependency
3. **Set up development environment** with test documents of various formats
4. **Begin Phase 1** implementation with `DocumentProcessor`
5. **Test with PDF, DOCX, MD, TXT** files
6. **Weekly reviews** after each phase
7. **User feedback integration** throughout process
8. **Production deployment** after Phase 5 completion

---

*This plan ensures working functionality at each phase, with clear deliverables and rollback options at every step.*