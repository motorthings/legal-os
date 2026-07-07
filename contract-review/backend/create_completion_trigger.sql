-- Create a function that automatically updates document processing_status when contract_analysis is inserted/updated
CREATE OR REPLACE FUNCTION update_document_processing_status()
RETURNS TRIGGER AS $$
BEGIN
    -- When a contract_analysis record is created/updated successfully, mark document as completed
    UPDATE documents
    SET 
        processing_status = 'completed',
        processed = true
    WHERE id = NEW.document_id
    AND processing_status != 'completed';  -- Only update if not already completed
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop existing trigger if it exists
DROP TRIGGER IF EXISTS trigger_update_document_status ON contract_analysis;

-- Create trigger that fires AFTER INSERT OR UPDATE on contract_analysis
CREATE TRIGGER trigger_update_document_status
    AFTER INSERT OR UPDATE ON contract_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_document_processing_status();

-- Backfill: Update all documents that have analysis but are still marked as pending
UPDATE documents d
SET 
    processing_status = 'completed',
    processed = true
FROM contract_analysis ca
WHERE d.id = ca.document_id
AND d.processing_status = 'pending';
