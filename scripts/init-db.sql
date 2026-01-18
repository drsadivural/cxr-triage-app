-- CXR Triage Database Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Studies table
CREATE TABLE IF NOT EXISTS studies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    accession_number VARCHAR(64),
    patient_id VARCHAR(64),
    study_date DATE,
    study_time TIME,
    modality VARCHAR(16) DEFAULT 'CR',
    view_position VARCHAR(16),
    body_part VARCHAR(32) DEFAULT 'CHEST',
    
    -- File paths
    original_file_path VARCHAR(512),
    processed_image_path VARCHAR(512),
    dicom_file_path VARCHAR(512),
    
    -- Analysis results
    status VARCHAR(32) DEFAULT 'pending',
    triage_level VARCHAR(16),
    triage_reasons JSONB,
    
    -- Report
    report_findings TEXT,
    report_impression TEXT,
    report_llm_rewritten BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    processing_time_ms INTEGER,
    error_message TEXT,
    model_info JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Findings table
CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    finding_name VARCHAR(64) NOT NULL,
    probability FLOAT NOT NULL,
    calibrated_probability FLOAT,
    status VARCHAR(16) NOT NULL,
    triage_threshold FLOAT DEFAULT 0.3,
    strong_threshold FLOAT DEFAULT 0.7,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bounding boxes table
CREATE TABLE IF NOT EXISTS bounding_boxes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    finding_name VARCHAR(64) NOT NULL,
    confidence FLOAT NOT NULL,
    x_min FLOAT NOT NULL,
    y_min FLOAT NOT NULL,
    x_max FLOAT NOT NULL,
    y_max FLOAT NOT NULL,
    x_min_px INTEGER,
    y_min_px INTEGER,
    x_max_px INTEGER,
    y_max_px INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_id UUID REFERENCES studies(id) ON DELETE SET NULL,
    action VARCHAR(64) NOT NULL,
    actor VARCHAR(128),
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(128) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    encrypted BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- QA Reviews table
CREATE TABLE IF NOT EXISTS qa_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    review_type VARCHAR(16) NOT NULL, -- FP, FN, TP, TN
    finding_name VARCHAR(64),
    reviewer VARCHAR(128),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_studies_status ON studies(status);
CREATE INDEX IF NOT EXISTS idx_studies_triage_level ON studies(triage_level);
CREATE INDEX IF NOT EXISTS idx_studies_created_at ON studies(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_studies_accession ON studies(accession_number);
CREATE INDEX IF NOT EXISTS idx_studies_patient ON studies(patient_id);

CREATE INDEX IF NOT EXISTS idx_findings_study ON findings(study_id);
CREATE INDEX IF NOT EXISTS idx_findings_name ON findings(finding_name);

CREATE INDEX IF NOT EXISTS idx_boxes_study ON bounding_boxes(study_id);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_study ON audit_logs(study_id);

CREATE INDEX IF NOT EXISTS idx_qa_study ON qa_reviews(study_id);
CREATE INDEX IF NOT EXISTS idx_qa_type ON qa_reviews(review_type);

-- Insert default settings
INSERT INTO settings (key, value) VALUES
    ('ai', '{
        "pneumothorax": {"triage_threshold": 0.3, "strong_threshold": 0.7, "enabled": true},
        "pleural_effusion": {"triage_threshold": 0.3, "strong_threshold": 0.7, "enabled": true},
        "consolidation": {"triage_threshold": 0.3, "strong_threshold": 0.7, "enabled": true},
        "cardiomegaly": {"triage_threshold": 0.4, "strong_threshold": 0.8, "enabled": true},
        "edema": {"triage_threshold": 0.3, "strong_threshold": 0.7, "enabled": true},
        "nodule": {"triage_threshold": 0.25, "strong_threshold": 0.6, "enabled": true},
        "mass": {"triage_threshold": 0.25, "strong_threshold": 0.6, "enabled": true},
        "detector_confidence": 0.25,
        "detector_iou": 0.45,
        "detector_max_boxes": 10,
        "calibration_enabled": true
    }'::jsonb),
    ('llm', '{
        "active_provider": null,
        "llm_rewrite_enabled": false,
        "azure_openai": {
            "enabled": false,
            "endpoint": "",
            "deployment_name": "",
            "api_version": "2024-02-15-preview",
            "api_key": "",
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 1024,
            "streaming": false
        },
        "claude": {
            "enabled": false,
            "base_url": "https://api.anthropic.com",
            "model": "claude-3-sonnet-20240229",
            "api_key": "",
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 1024
        },
        "gemini": {
            "enabled": false,
            "base_url": "https://generativelanguage.googleapis.com",
            "model": "gemini-pro",
            "api_key": "",
            "temperature": 0.3,
            "top_p": 0.95,
            "max_output_tokens": 1024
        }
    }'::jsonb),
    ('database', '{
        "db_type": "postgres",
        "host": "db",
        "port": 5432,
        "user": "cxr_user",
        "password": "cxr_password",
        "dbname": "cxr_triage",
        "ssl_mode": "disable"
    }'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for studies table
DROP TRIGGER IF EXISTS update_studies_updated_at ON studies;
CREATE TRIGGER update_studies_updated_at
    BEFORE UPDATE ON studies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for settings table
DROP TRIGGER IF EXISTS update_settings_updated_at ON settings;
CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
