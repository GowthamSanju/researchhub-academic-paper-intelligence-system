-- =====================================================
-- Legal Document Analysis - Sample Database Schema
-- =====================================================
-- This SQL file contains sample data for the Legal RAG System
-- It includes case law metadata, contract clause indices, and reference data
-- =====================================================

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- TABLE 1: Case Law Metadata
-- =====================================================
DROP TABLE IF EXISTS case_law_metadata CASCADE;

CREATE TABLE case_law_metadata (
    case_id SERIAL PRIMARY KEY,
    case_number VARCHAR(100) UNIQUE NOT NULL,
    case_title TEXT NOT NULL,
    court_name VARCHAR(200) NOT NULL,
    jurisdiction VARCHAR(100) NOT NULL,
    filing_date DATE NOT NULL,
    decision_date DATE,
    case_type VARCHAR(100) NOT NULL,
    case_status VARCHAR(50) NOT NULL,
    primary_judge VARCHAR(200),
    citation TEXT,
    keywords TEXT[],
    summary TEXT,
    legal_act_references TEXT[],
    embedding vector(1536),  -- For semantic search
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data for Case Law Metadata
INSERT INTO case_law_metadata 
(case_number, case_title, court_name, jurisdiction, filing_date, decision_date, case_type, case_status, primary_judge, citation, keywords, summary, legal_act_references) 
VALUES
('2023/SCC/0045', 'Sharma Industries Ltd. vs. Global Tech Solutions Pvt. Ltd.', 'Supreme Court of India', 'India', '2022-03-15', '2023-02-10', 'Contract Dispute', 'Decided', 'Justice R.K. Malhotra', '(2023) 3 SCC 245', 
ARRAY['breach of contract', 'damages', 'specific performance', 'limitation period'], 
'The case involved a breach of service agreement where the defendant failed to deliver contracted software solutions within the agreed timeline. The Court held that mere delay without valid justification constitutes material breach and awarded damages based on actual losses suffered by the plaintiff.',
ARRAY['Indian Contract Act, 1872 - Section 73', 'Specific Relief Act, 1963 - Section 10', 'Limitation Act, 1963 - Article 113']),

('2023/HC-BLR/1234', 'DataVision Enterprises Ltd. vs. CloudServe India Pvt. Ltd.', 'Karnataka High Court', 'Karnataka', '2022-08-20', '2023-05-15', 'Contract Dispute', 'Decided', 'Justice Meena Krishnamurthy', '2023 KarHC 567', 
ARRAY['cloud services', 'data breach', 'indemnification', 'confidentiality'], 
'Dispute arising from alleged data breach in cloud storage services. The Court examined the liability clauses and held that service providers must implement industry-standard security measures and cannot exclude liability for gross negligence through contractual indemnification clauses.',
ARRAY['Information Technology Act, 2000 - Section 43', 'Indian Contract Act, 1872 - Section 23']),

('2022/HC-DEL/5678', 'TechConsult Solutions Pvt. Ltd. vs. Finance Corp Limited', 'Delhi High Court', 'Delhi', '2021-11-10', '2022-09-22', 'Intellectual Property', 'Decided', 'Justice Arvind Kumar', '2022 DelhiHC 892', 
ARRAY['intellectual property', 'trade secrets', 'non-compete', 'injunction'], 
'The case dealt with alleged misappropriation of proprietary methodologies and client lists after termination of service agreement. The Court granted interim injunction restraining the defendant from using confidential information and enforced the non-compete clause for a reasonable period.',
ARRAY['Indian Contract Act, 1872 - Section 27', 'Specific Relief Act, 1963 - Section 41']),

('2023/HC-MUM/3456', 'Legal Associates LLP vs. Corporate Services India Ltd.', 'Bombay High Court', 'Maharashtra', '2022-06-05', '2023-03-18', 'Professional Services', 'Decided', 'Justice Priya Deshmukh', '2023 BomHC 234', 
ARRAY['professional negligence', 'duty of care', 'limitation of liability', 'expert testimony'], 
'Professional negligence claim against legal service providers. The Court held that professionals owe a duty of care to their clients and limitation of liability clauses must be reasonable and cannot exclude liability for gross negligence or willful misconduct.',
ARRAY['Indian Contract Act, 1872 - Section 73', 'Limitation Act, 1963 - Article 113']),

('2024/SCC/0012', 'Innovation Labs Pvt. Ltd. vs. Digital Solutions Group', 'Supreme Court of India', 'India', '2023-01-12', '2024-01-05', 'Contract Termination', 'Decided', 'Justice S.K. Verma', '(2024) 1 SCC 112', 
ARRAY['termination', 'notice period', 'severance', 'work product ownership'], 
'The case addressed the validity of contract termination and ownership of work product created during the contract period. The Supreme Court clarified that intellectual property created during the subsistence of contract belongs to the client unless explicitly agreed otherwise.',
ARRAY['Copyright Act, 1957 - Section 17', 'Indian Contract Act, 1872 - Section 64']);

-- =====================================================
-- TABLE 2: Contract Clause Index
-- =====================================================
DROP TABLE IF EXISTS contract_clause_index CASCADE;

CREATE TABLE contract_clause_index (
    clause_id SERIAL PRIMARY KEY,
    contract_id VARCHAR(100) NOT NULL,
    contract_name TEXT NOT NULL,
    contract_type VARCHAR(100) NOT NULL,
    clause_type VARCHAR(100) NOT NULL,
    clause_title TEXT NOT NULL,
    clause_number VARCHAR(50),
    clause_text TEXT NOT NULL,
    page_number INTEGER,
    risk_level VARCHAR(20),  -- Low, Medium, High, Critical
    keywords TEXT[],
    related_clauses INTEGER[],  -- References to other clause_ids
    embedding vector(1536),  -- For semantic search
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data for Contract Clause Index
INSERT INTO contract_clause_index 
(contract_id, contract_name, contract_type, clause_type, clause_title, clause_number, clause_text, page_number, risk_level, keywords) 
VALUES
('PSA-2024-1157', 'Professional Services Agreement - TechConsult & DataVision', 'Service Agreement', 'Termination', 'Termination for Convenience', '3.2', 
'Either party may terminate this Agreement upon providing sixty (60) days prior written notice to the other party. In the event of such termination, Client shall pay Provider for all services rendered up to the effective date of termination, including any work in progress calculated on a pro-rata basis.', 
1, 'Medium', 
ARRAY['termination', 'notice period', 'payment obligation', 'work in progress']),

('PSA-2024-1157', 'Professional Services Agreement - TechConsult & DataVision', 'Service Agreement', 'Termination', 'Termination for Cause', '3.3', 
'Either party may terminate this Agreement immediately upon written notice if the other party: (a) commits a material breach of any provision of this Agreement and fails to cure such breach within thirty (30) days of receiving written notice thereof; or (b) becomes insolvent, makes an assignment for the benefit of creditors, or has a receiver appointed for its business or assets.', 
1, 'High', 
ARRAY['material breach', 'cure period', 'insolvency', 'immediate termination']),

('PSA-2024-1157', 'Professional Services Agreement - TechConsult & DataVision', 'Service Agreement', 'Confidentiality', 'Confidential Information Definition', '4.1', 
'Confidential Information means all non-public information disclosed by either party (Disclosing Party) to the other party (Receiving Party), whether orally, in writing, or in electronic form, including but not limited to technical data, trade secrets, know-how, research, product plans, customer lists, financial information, and business strategies.', 
2, 'High', 
ARRAY['confidential information', 'trade secrets', 'disclosure', 'protected information']),

('PSA-2024-1157', 'Professional Services Agreement - TechConsult & DataVision', 'Service Agreement', 'Confidentiality', 'Confidentiality Obligations', '4.2', 
'The Receiving Party shall: (a) maintain the confidentiality of all Confidential Information using the same degree of care it uses to protect its own confidential information, but in no event less than reasonable care; (b) not disclose Confidential Information to any third party without prior written consent; and (c) use Confidential Information solely for the purpose of performing its obligations under this Agreement.', 
2, 'Critical', 
ARRAY['confidentiality obligations', 'standard of care', 'non-disclosure', 'permitted use']),

('PSA-2024-1157', 'Professional Services Agreement - TechConsult & DataVision', 'Service Agreement', 'Intellectual Property', 'Ownership of Deliverables', '5.1', 
'All intellectual property rights in the deliverables created specifically for Client under this Agreement, including custom software code, documentation, and training materials, shall vest in and be the exclusive property of the Client upon full payment of all fees due hereunder.', 
2, 'Critical', 
ARRAY['intellectual property', 'ownership', 'deliverables', 'work product', 'payment condition']),

('PSA-2024-1157', 'Professional Services Agreement - TechConsult & DataVision', 'Service Agreement', 'Intellectual Property', 'Pre-existing Materials', '5.2', 
'Provider retains all rights to its pre-existing intellectual property, including frameworks, libraries, tools, and methodologies. Client is granted a non-exclusive, perpetual, royalty-free license to use such pre-existing materials solely as incorporated in the deliverables for Clients internal business purposes.', 
2, 'Medium', 
ARRAY['pre-existing IP', 'license grant', 'background technology', 'usage rights']),

('PSA-2024-1157', 'Professional Services Agreement - TechConsult & DataVision', 'Service Agreement', 'Liability', 'Limitation of Liability', '6', 
'To the maximum extent permitted by applicable law, in no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages, including but not limited to loss of profits, loss of data, or business interruption, arising out of or relating to this Agreement, even if advised of the possibility of such damages. The total cumulative liability of Provider under this Agreement shall not exceed the total fees paid by Client to Provider in the twelve (12) months preceding the event giving rise to such liability.', 
2, 'Critical', 
ARRAY['limitation of liability', 'consequential damages', 'liability cap', 'exclusions']),

('PSA-2024-1157', 'Professional Services Agreement - TechConsult & DataVision', 'Service Agreement', 'Payment', 'Payment Schedule', '2', 
'Client agrees to pay Provider the fees as set forth in the payment schedule. Payment shall be made within thirty (30) days of receipt of invoice for each milestone. All amounts are exclusive of applicable Goods and Services Tax (GST) at 18%, which shall be charged additionally.', 
1, 'Medium', 
ARRAY['payment terms', 'milestone payments', 'invoice', 'GST', 'payment period']);

-- =====================================================
-- TABLE 3: Legal Acts and Statutes Reference
-- =====================================================
DROP TABLE IF EXISTS legal_acts_reference CASCADE;

CREATE TABLE legal_acts_reference (
    act_id SERIAL PRIMARY KEY,
    act_name TEXT NOT NULL,
    act_short_name VARCHAR(200),
    jurisdiction VARCHAR(100) NOT NULL,
    enactment_year INTEGER NOT NULL,
    category VARCHAR(100) NOT NULL,
    section_number VARCHAR(50),
    section_title TEXT,
    section_description TEXT,
    application_notes TEXT,
    keywords TEXT[],
    related_cases INTEGER[],  -- References to case_law_metadata.case_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data for Legal Acts Reference
INSERT INTO legal_acts_reference 
(act_name, act_short_name, jurisdiction, enactment_year, category, section_number, section_title, section_description, application_notes, keywords) 
VALUES
('The Indian Contract Act, 1872', 'Contract Act', 'India', 1872, 'Commercial Law', '73', 
'Compensation for loss or damage caused by breach of contract', 
'When a contract has been broken, the party who suffers by such breach is entitled to receive, from the party who has broken the contract, compensation for any loss or damage caused to him thereby, which naturally arose in the usual course of things from such breach, or which the parties knew, when they made the contract, to be likely to result from the breach of it.',
'This section forms the basis for claiming damages in breach of contract cases. Courts have held that damages must be foreseeable and quantifiable. Remote or speculative damages are not recoverable.',
ARRAY['damages', 'breach of contract', 'compensation', 'foreseeability', 'remoteness']),

('The Indian Contract Act, 1872', 'Contract Act', 'India', 1872, 'Commercial Law', '27', 
'Agreement in restraint of trade, void', 
'Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void. Exception 1 - One who sells the goodwill of a business may agree with the buyer to refrain from carrying on a similar business, within specified local limits, so long as the buyer, or any person deriving title to the goodwill from him, carries on a like business therein.',
'Non-compete clauses are generally void under Indian law except in the case of sale of goodwill. However, courts have upheld reasonable restraints during the subsistence of employment or contract to protect confidential information.',
ARRAY['non-compete', 'restraint of trade', 'goodwill', 'enforceability']),

('The Specific Relief Act, 1963', 'Specific Relief Act', 'India', 1963, 'Remedies', '10', 
'Cases in which specific performance of contract enforceable', 
'Except as otherwise provided in this Chapter, the specific performance of any contract may, in the discretion of the court, be enforced when the act agreed to be done is such that compensation in money for its non-performance would not afford adequate relief.',
'Specific performance is an equitable remedy and is granted at the discretion of the court. It is typically ordered when the subject matter is unique and damages would be inadequate. Real property contracts are common examples.',
ARRAY['specific performance', 'equitable remedy', 'inadequacy of damages', 'discretion']),

('The Information Technology Act, 2000', 'IT Act', 'India', 2000, 'Technology Law', '43', 
'Penalty and compensation for damage to computer, computer system, etc.', 
'If any person without permission of the owner or any other person who is in charge of a computer, computer system or computer network, accesses or secures access to such computer, computer system or computer network or downloads, copies or extracts any data, computer database or information from such computer, computer system or computer network, he shall be liable to pay damages by way of compensation to the person so affected.',
'This section is crucial in data breach and cybersecurity cases. It establishes civil liability for unauthorized access and data theft. Often used in conjunction with contract law provisions regarding data protection.',
ARRAY['data breach', 'unauthorized access', 'compensation', 'cybersecurity', 'computer systems']),

('The Limitation Act, 1963', 'Limitation Act', 'India', 1963, 'Procedural Law', 'Article 113', 
'Suit upon a contract', 
'A suit upon a contract must be filed within three years from the date when the right to sue accrues. For breach of contract, the limitation period begins from the date of breach.',
'Limitation is crucial in contract disputes. Once the limitation period expires, the claim becomes time-barred. The period can be extended in cases of fraud, concealment, or acknowledgment of liability.',
ARRAY['limitation period', 'time-barred', 'statute of limitations', 'contract suits']);

-- =====================================================
-- TABLE 4: Document Metadata (for RAG system tracking)
-- =====================================================
DROP TABLE IF EXISTS document_metadata CASCADE;

CREATE TABLE document_metadata (
    document_id SERIAL PRIMARY KEY,
    document_name TEXT NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    file_path TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    document_date DATE,
    parties_involved TEXT[],
    total_pages INTEGER,
    file_size_bytes BIGINT,
    processing_status VARCHAR(50),
    chunk_count INTEGER,
    keywords TEXT[],
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data for Document Metadata
INSERT INTO document_metadata 
(document_name, document_type, file_path, document_date, parties_involved, total_pages, file_size_bytes, processing_status, chunk_count, keywords, summary) 
VALUES
('Professional Services Agreement - PSA-2024-1157', 'Contract', '/documents/contracts/PSA-2024-1157.docx', '2024-01-15', 
ARRAY['TechConsult Solutions Pvt. Ltd.', 'DataVision Enterprises Ltd.'], 
2, 156789, 'Processed', 15, 
ARRAY['service agreement', 'AI system development', 'legal tech', 'payment terms', 'IP rights'],
'Service agreement for development of AI-powered legal document management system between TechConsult Solutions and DataVision Enterprises, valued at Rs. 76.25 lakhs with three-phase delivery.'),

('Non-Disclosure Agreement - NDA-2023-892', 'Contract', '/documents/contracts/NDA-2023-892.pdf', '2023-08-10', 
ARRAY['Innovation Labs Pvt. Ltd.', 'Research Technologies Inc.'], 
5, 234567, 'Processed', 12, 
ARRAY['confidentiality', 'mutual NDA', 'proprietary information', 'exclusions'],
'Mutual non-disclosure agreement for exchange of proprietary information related to collaborative research project in machine learning applications.'),

('Employment Service Contract - ESC-2024-045', 'Contract', '/documents/contracts/ESC-2024-045.pdf', '2024-02-01', 
ARRAY['Global Tech Consulting Ltd.', 'Sharma, Rajesh Kumar'], 
8, 445678, 'Processed', 22, 
ARRAY['employment', 'non-compete', 'IP assignment', 'confidentiality', 'termination'],
'Senior consultant employment agreement including comprehensive IP assignment, 12-month non-compete clause, and performance-based compensation structure.');

-- =====================================================
-- INDEXES for Performance Optimization
-- =====================================================

-- Indexes for case_law_metadata
CREATE INDEX idx_case_law_case_number ON case_law_metadata(case_number);
CREATE INDEX idx_case_law_court ON case_law_metadata(court_name);
CREATE INDEX idx_case_law_jurisdiction ON case_law_metadata(jurisdiction);
CREATE INDEX idx_case_law_status ON case_law_metadata(case_status);
CREATE INDEX idx_case_law_decision_date ON case_law_metadata(decision_date);
CREATE INDEX idx_case_law_keywords ON case_law_metadata USING GIN(keywords);
CREATE INDEX idx_case_law_embedding ON case_law_metadata USING ivfflat (embedding vector_cosine_ops);

-- Indexes for contract_clause_index
CREATE INDEX idx_clause_contract_id ON contract_clause_index(contract_id);
CREATE INDEX idx_clause_type ON contract_clause_index(clause_type);
CREATE INDEX idx_clause_risk ON contract_clause_index(risk_level);
CREATE INDEX idx_clause_keywords ON contract_clause_index USING GIN(keywords);
CREATE INDEX idx_clause_embedding ON contract_clause_index USING ivfflat (embedding vector_cosine_ops);

-- Indexes for legal_acts_reference
CREATE INDEX idx_act_jurisdiction ON legal_acts_reference(jurisdiction);
CREATE INDEX idx_act_category ON legal_acts_reference(category);
CREATE INDEX idx_act_section ON legal_acts_reference(section_number);
CREATE INDEX idx_act_keywords ON legal_acts_reference USING GIN(keywords);

-- Indexes for document_metadata
CREATE INDEX idx_doc_type ON document_metadata(document_type);
CREATE INDEX idx_doc_status ON document_metadata(processing_status);
CREATE INDEX idx_doc_date ON document_metadata(document_date);
CREATE INDEX idx_doc_keywords ON document_metadata USING GIN(keywords);

-- =====================================================
-- Sample Queries for Testing
-- =====================================================

-- Query 1: Find all contracts related to confidentiality
-- SELECT * FROM contract_clause_index 
-- WHERE clause_type = 'Confidentiality' 
-- ORDER BY risk_level DESC;

-- Query 2: Find case law related to breach of contract
-- SELECT case_number, case_title, court_name, decision_date 
-- FROM case_law_metadata 
-- WHERE 'breach of contract' = ANY(keywords)
-- ORDER BY decision_date DESC;

-- Query 3: Find high-risk clauses in a specific contract
-- SELECT clause_title, clause_type, clause_text, risk_level 
-- FROM contract_clause_index 
-- WHERE contract_id = 'PSA-2024-1157' AND risk_level IN ('High', 'Critical')
-- ORDER BY clause_number;

-- Query 4: Find legal provisions related to damages
-- SELECT act_name, section_number, section_title 
-- FROM legal_acts_reference 
-- WHERE 'damages' = ANY(keywords)
-- ORDER BY enactment_year;

-- Query 5: Get contract overview with clause count by risk level
-- SELECT 
--     contract_id,
--     contract_name,
--     risk_level,
--     COUNT(*) as clause_count
-- FROM contract_clause_index
-- WHERE contract_id = 'PSA-2024-1157'
-- GROUP BY contract_id, contract_name, risk_level
-- ORDER BY 
--     CASE risk_level
--         WHEN 'Critical' THEN 1
--         WHEN 'High' THEN 2
--         WHEN 'Medium' THEN 3
--         WHEN 'Low' THEN 4
--     END;
