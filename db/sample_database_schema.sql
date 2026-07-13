-- ========================================
-- ResearchHub Academic Paper Metadata Database
-- Sample Data for RAG System Development
-- ========================================

-- Table: papers
-- Stores core metadata about academic papers
CREATE TABLE papers (
    paper_id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    abstract TEXT,
    publication_year INTEGER,
    publication_venue VARCHAR(200),
    doi VARCHAR(100) UNIQUE,
    arxiv_id VARCHAR(50),
    citation_count INTEGER DEFAULT 0,
    pdf_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: authors
-- Stores information about researchers and authors
CREATE TABLE authors (
    author_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    affiliation VARCHAR(300),
    email VARCHAR(200),
    orcid VARCHAR(50),
    h_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: paper_authors
-- Many-to-many relationship between papers and authors
CREATE TABLE paper_authors (
    paper_id INTEGER REFERENCES papers(paper_id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES authors(author_id) ON DELETE CASCADE,
    author_position INTEGER, -- 1 for first author, 2 for second, etc.
    is_corresponding BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (paper_id, author_id)
);

-- Table: keywords
-- Stores research keywords and topics
CREATE TABLE keywords (
    keyword_id SERIAL PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(100) -- e.g., 'Machine Learning', 'NLP', 'Computer Vision'
);

-- Table: paper_keywords
-- Many-to-many relationship between papers and keywords
CREATE TABLE paper_keywords (
    paper_id INTEGER REFERENCES papers(paper_id) ON DELETE CASCADE,
    keyword_id INTEGER REFERENCES keywords(keyword_id) ON DELETE CASCADE,
    PRIMARY KEY (paper_id, keyword_id)
);

-- Table: citations
-- Tracks citations between papers
CREATE TABLE citations (
    citing_paper_id INTEGER REFERENCES papers(paper_id) ON DELETE CASCADE,
    cited_paper_id INTEGER REFERENCES papers(paper_id) ON DELETE CASCADE,
    citation_context TEXT, -- Optional: text surrounding the citation
    PRIMARY KEY (citing_paper_id, cited_paper_id)
);

-- ========================================
-- SAMPLE DATA
-- ========================================

-- Insert sample papers
INSERT INTO papers (title, abstract, publication_year, publication_venue, doi, arxiv_id, citation_count, pdf_path) VALUES
(
    'Efficient Attention Mechanisms for Transformer Models: A Comparative Analysis',
    'Transformer models have revolutionized natural language processing, but their quadratic computational complexity with respect to sequence length poses significant challenges for scaling. This paper presents a comprehensive analysis of four attention mechanisms designed to improve transformer efficiency: standard self-attention, sparse attention, linear attention, and flash attention.',
    2024,
    'Conference on Neural Information Processing Systems (NeurIPS)',
    '10.5555/neurips2024.12345',
    'arXiv:2401.00001',
    127,
    '/data/papers/chen_et_al_2024_efficient_attention.pdf'
),
(
    'Attention Is All You Need',
    'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.',
    2017,
    'Advances in Neural Information Processing Systems',
    '10.5555/nips2017.7181',
    'arXiv:1706.03762',
    89453,
    '/data/papers/vaswani_et_al_2017_attention.pdf'
),
(
    'FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness',
    'Transformers are slow and memory-hungry on long sequences, since the time and memory complexity of self-attention are quadratic in sequence length. Approximate attention methods have attempted to address this problem by trading off model quality to reduce the compute complexity, but often do not achieve wall-clock speedup.',
    2022,
    'Advances in Neural Information Processing Systems',
    '10.5555/nips2022.9001',
    'arXiv:2205.14135',
    2891,
    '/data/papers/dao_et_al_2022_flashattention.pdf'
),
(
    'Generating Long Sequences with Sparse Transformers',
    'Transformers have shown great success in modeling a variety of data modalities. However, the quadratic complexity of the attention mechanism limits their application to long sequences. We introduce sparse factorizations of the attention matrix which reduce this to O(n sqrt(n)) in time and space.',
    2019,
    'arXiv preprint',
    NULL,
    'arXiv:1904.10509',
    1247,
    '/data/papers/child_et_al_2019_sparse.pdf'
),
(
    'Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention',
    'Transformers achieve remarkable performance in several tasks but due to their quadratic complexity, with respect to the input sequence, they are prohibitively slow for very long sequences. We express the self-attention as a linear dot-product of kernel feature maps and make use of the associativity property of matrix products.',
    2020,
    'International Conference on Machine Learning (ICML)',
    '10.5555/icml2020.5678',
    'arXiv:2006.16236',
    983,
    '/data/papers/katharopoulos_et_al_2020_linear.pdf'
),
(
    'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
    'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context.',
    2019,
    'North American Chapter of the Association for Computational Linguistics (NAACL)',
    '10.18653/v1/N19-1423',
    'arXiv:1810.04805',
    67821,
    '/data/papers/devlin_et_al_2019_bert.pdf'
);

-- Insert sample authors
INSERT INTO authors (name, affiliation, email, orcid, h_index) VALUES
('Sarah Chen', 'Stanford University', 'schen@stanford.edu', '0000-0001-1234-5678', 42),
('Michael Rodriguez', 'Stanford University', 'mrodriguez@stanford.edu', '0000-0002-2345-6789', 38),
('Aisha Patel', 'Stanford University', 'apatel@stanford.edu', '0000-0003-3456-7890', 35),
('Ashish Vaswani', 'Google Brain', 'avaswani@google.com', '0000-0004-4567-8901', 156),
('Noam Shazeer', 'Google Brain', 'noam@google.com', '0000-0005-5678-9012', 143),
('Tri Dao', 'Princeton University', 'tridao@princeton.edu', '0000-0006-6789-0123', 48),
('Daniel Y. Fu', 'Stanford University', 'danfu@stanford.edu', '0000-0007-7890-1234', 31),
('Rewon Child', 'OpenAI', 'rewon@openai.com', '0000-0008-8901-2345', 52),
('Angelos Katharopoulos', 'ETH Zurich', 'angelos.katharopoulos@inf.ethz.ch', '0000-0009-9012-3456', 29),
('Jacob Devlin', 'Google Research', 'jacobdevlin@google.com', '0000-0010-0123-4567', 128);

-- Link papers to authors
INSERT INTO paper_authors (paper_id, author_id, author_position, is_corresponding) VALUES
-- Paper 1: Efficient Attention Mechanisms
(1, 1, 1, TRUE),   -- Sarah Chen (first & corresponding)
(1, 2, 2, FALSE),  -- Michael Rodriguez
(1, 3, 3, FALSE),  -- Aisha Patel
-- Paper 2: Attention Is All You Need
(2, 4, 1, FALSE),  -- Ashish Vaswani
(2, 5, 2, FALSE),  -- Noam Shazeer
-- Paper 3: FlashAttention
(3, 6, 1, TRUE),   -- Tri Dao
(3, 7, 2, FALSE),  -- Daniel Y. Fu
-- Paper 4: Sparse Transformers
(4, 8, 1, TRUE),   -- Rewon Child
-- Paper 5: Linear Attention
(5, 9, 1, TRUE),   -- Angelos Katharopoulos
-- Paper 6: BERT
(6, 10, 1, TRUE);  -- Jacob Devlin

-- Insert keywords
INSERT INTO keywords (keyword, category) VALUES
('transformer models', 'Deep Learning'),
('attention mechanisms', 'Deep Learning'),
('computational efficiency', 'Performance Optimization'),
('deep learning optimization', 'Performance Optimization'),
('natural language processing', 'NLP'),
('self-attention', 'Deep Learning'),
('sparse attention', 'Deep Learning'),
('linear attention', 'Deep Learning'),
('flash attention', 'Deep Learning'),
('language models', 'NLP'),
('BERT', 'NLP'),
('sequence modeling', 'Deep Learning'),
('neural architecture', 'Deep Learning'),
('GPU optimization', 'Performance Optimization'),
('memory efficiency', 'Performance Optimization');

-- Link papers to keywords
INSERT INTO paper_keywords (paper_id, keyword_id) VALUES
-- Paper 1: Efficient Attention Mechanisms
(1, 1), (1, 2), (1, 3), (1, 4), (1, 7), (1, 8), (1, 9),
-- Paper 2: Attention Is All You Need
(2, 1), (2, 2), (2, 5), (2, 6), (2, 12), (2, 13),
-- Paper 3: FlashAttention
(3, 1), (3, 2), (3, 9), (3, 14), (3, 15),
-- Paper 4: Sparse Transformers
(4, 1), (4, 7), (4, 12), (4, 13),
-- Paper 5: Linear Attention
(5, 1), (5, 8), (5, 12), (5, 3),
-- Paper 6: BERT
(6, 1), (6, 5), (6, 10), (6, 11);

-- Insert citation relationships
INSERT INTO citations (citing_paper_id, cited_paper_id, citation_context) VALUES
-- Paper 1 cites Papers 2, 3, 4, 5
(1, 2, 'The transformer architecture introduced by Vaswani et al. (2017) has become the foundation...'),
(1, 3, 'Flash attention optimizes memory access patterns for modern hardware accelerators...'),
(1, 4, 'Sparse attention patterns reduce computation by limiting attention to specific positions...'),
(1, 5, 'Linear attention mechanisms approximate attention with linear complexity...'),
-- Paper 3 cites Paper 2
(3, 2, 'Building on the original transformer architecture...'),
-- Paper 4 cites Paper 2
(4, 2, 'The attention mechanism from Vaswani et al. enables...'),
-- Paper 5 cites Paper 2
(5, 2, 'Transformers rely on the self-attention mechanism...'),
-- Paper 6 cites Paper 2
(6, 2, 'We build upon the transformer architecture...');

-- ========================================
-- SAMPLE QUERIES FOR TESTING
-- ========================================

-- Query 1: Find all papers by a specific author
-- SELECT p.title, p.publication_year, p.citation_count
-- FROM papers p
-- JOIN paper_authors pa ON p.paper_id = pa.paper_id
-- JOIN authors a ON pa.author_id = a.author_id
-- WHERE a.name = 'Sarah Chen';

-- Query 2: Find papers with most citations in a given year
-- SELECT title, citation_count, publication_venue
-- FROM papers
-- WHERE publication_year = 2024
-- ORDER BY citation_count DESC
-- LIMIT 5;

-- Query 3: Find papers by keyword
-- SELECT DISTINCT p.title, p.publication_year, p.citation_count
-- FROM papers p
-- JOIN paper_keywords pk ON p.paper_id = pk.paper_id
-- JOIN keywords k ON pk.keyword_id = k.keyword_id
-- WHERE k.keyword = 'flash attention';

-- Query 4: Find co-authors of a specific researcher
-- SELECT DISTINCT a2.name, a2.affiliation
-- FROM authors a1
-- JOIN paper_authors pa1 ON a1.author_id = pa1.author_id
-- JOIN paper_authors pa2 ON pa1.paper_id = pa2.paper_id
-- JOIN authors a2 ON pa2.author_id = a2.author_id
-- WHERE a1.name = 'Tri Dao' AND a2.name != 'Tri Dao';

-- Query 5: Find papers that cite a specific paper
-- SELECT p.title, p.publication_year
-- FROM papers p
-- JOIN citations c ON p.paper_id = c.citing_paper_id
-- WHERE c.cited_paper_id = (SELECT paper_id FROM papers WHERE title = 'Attention Is All You Need');

-- Query 6: Find most cited papers in a research area
-- SELECT p.title, p.citation_count, p.publication_year
-- FROM papers p
-- JOIN paper_keywords pk ON p.paper_id = pk.paper_id
-- JOIN keywords k ON pk.keyword_id = k.keyword_id
-- WHERE k.category = 'Deep Learning'
-- GROUP BY p.paper_id, p.title, p.citation_count, p.publication_year
-- ORDER BY p.citation_count DESC
-- LIMIT 10;

-- Query 7: Author productivity and impact
-- SELECT a.name, a.affiliation, 
--        COUNT(DISTINCT pa.paper_id) as paper_count,
--        SUM(p.citation_count) as total_citations,
--        a.h_index
-- FROM authors a
-- JOIN paper_authors pa ON a.author_id = pa.author_id
-- JOIN papers p ON pa.paper_id = p.paper_id
-- GROUP BY a.author_id, a.name, a.affiliation, a.h_index
-- ORDER BY total_citations DESC;
