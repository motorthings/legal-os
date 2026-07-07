#!/bin/bash
# Demo Data Setup Script
# Creates test documents for tomorrow's demo

echo "🎬 Setting up demo test data..."
echo ""

# Create test documents directory
mkdir -p /tmp/demo_documents

# 1. White Rabbit document (for KB retrieval demo)
cat > /tmp/demo_documents/white_rabbit_facts.txt << 'EOF'
# Fun Facts About White Rabbits

White rabbits are fascinating creatures with several interesting characteristics:

## Physical Characteristics

1. **Albinism**: True white rabbits have a genetic condition called albinism, which results in white fur and pink eyes due to the absence of melanin pigment.

2. **Size**: White rabbits can range from small dwarf breeds (2-3 pounds) to large breeds like the Flemish Giant (15-20 pounds).

3. **Lifespan**: Pet white rabbits typically live 8-12 years with proper care, though some can live even longer.

## Cultural Significance

1. **Symbolism**: In many cultures, white rabbits symbolize:
   - Luck and good fortune
   - Purity and innocence
   - Transformation and new beginnings
   - Fertility and rebirth

2. **Famous White Rabbits**:
   - The White Rabbit from Lewis Carroll's "Alice's Adventures in Wonderland"
   - The white rabbit in "The Matrix" (Follow the white rabbit)
   - Bugs Bunny occasionally appears in white form
   - The White Rabbit of Inaba from Japanese folklore

## Care Requirements

1. **Sun Sensitivity**: White rabbits with pink eyes are more sensitive to bright sunlight and may need extra protection for their eyes and skin.

2. **Diet**: Like all rabbits, they need:
   - Unlimited hay (timothy or orchard grass)
   - Fresh vegetables daily
   - Limited pellets
   - Fresh water

3. **Environment**: White rabbits need:
   - Spacious enclosure (at least 12 square feet)
   - Safe areas for exercise
   - Protection from extreme temperatures
   - Regular veterinary check-ups

## Interesting Behaviors

1. **Binky**: When happy, rabbits perform a jump and twist called a "binky"
2. **Chinning**: Rabbits mark territory by rubbing their chin on objects
3. **Thumping**: They thump their hind legs to signal danger
4. **Nose Wiggles**: A fast nose wiggle often indicates curiosity or excitement

## White Rabbit Breeds

Popular white rabbit breeds include:
- New Zealand White (popular for show and meat production)
- Florida White (compact and docile)
- American White (rare heritage breed)
- Himalayan (white with colored points)
- Polish (small and elegant)

White rabbits make wonderful pets for the right family. They require daily interaction, proper care, and a commitment to their wellbeing throughout their 8-12 year lifespan.
EOF

echo "✅ Created: /tmp/demo_documents/white_rabbit_facts.txt"

# 2. Generic demo document
cat > /tmp/demo_documents/demo_test_general.txt << 'EOF'
# SuperAssistant Demo Test Document

This is a general test document for verifying document upload and processing functionality.

## About SuperAssistant

SuperAssistant is an AI-powered executive assistant designed to help leaders with:

### Strategic Planning
- Long-term vision development
- OKR and goal setting
- Strategic initiative tracking
- Quarterly planning reviews

### Operational Support
- Task prioritization using TRIPS methodology
- Team delegation and workload balancing
- Meeting preparation and follow-up
- Document organization and retrieval

### Knowledge Management
- Document upload and processing
- Semantic search across your knowledge base
- Context-aware responses
- Citation and source tracking

## Key Features Demonstrated Today

1. **Performance Improvements**: 50-100x faster API responses
2. **Knowledge Base Retrieval**: Works with any document type
3. **Document Management**: Clean UI, no duplicates
4. **Modular Library System**: Industry-agnostic architecture
5. **TRIPS/LTEM Extraction**: Voice-first interview approach
6. **Chat Quality**: Well-formatted, professional responses

## Technical Architecture

SuperAssistant uses:
- FastAPI backend
- Supabase PostgreSQL with pgvector
- Anthropic Claude Sonnet 4.5
- Voyage AI embeddings
- RAG (Retrieval Augmented Generation)

This document should be chunked and indexed successfully for the demo.
EOF

echo "✅ Created: /tmp/demo_documents/demo_test_general.txt"

# 3. Quick performance test document
cat > /tmp/demo_documents/performance_test.txt << 'EOF'
Performance Test Document

This is a simple document to test upload and processing speed.

Expected processing time: 2-5 seconds
Expected chunks: 2-3

If this takes longer than 10 seconds, there may be an issue with the document processing pipeline.
EOF

echo "✅ Created: /tmp/demo_documents/performance_test.txt"

# 4. Strategic document example
cat > /tmp/demo_documents/q1_strategic_priorities.txt << 'EOF'
# Q1 2025 Strategic Priorities

## Executive Summary

This quarter focuses on three key areas: product innovation, market expansion, and operational efficiency. Our goal is to position the company for sustained growth while maintaining quality and team wellbeing.

## Key Initiatives

### 1. Product Innovation
**Objective:** Launch new AI-powered features

**Success Metrics:**
- Feature completion by March 15
- 90% user satisfaction score
- 25% increase in feature adoption

**Timeline:**
- January: Design and prototyping
- February: Development and testing
- March: Beta launch and iteration

### 2. Market Expansion
**Objective:** Enter two new geographic markets

**Success Metrics:**
- 50 new customers in target markets
- $500K revenue from new markets
- 3 strategic partnerships established

**Timeline:**
- January: Market research and partner identification
- February: Go-to-market strategy development
- March: Launch campaigns

### 3. Operational Efficiency
**Objective:** Streamline internal processes

**Success Metrics:**
- 30% reduction in operational overhead
- 50% decrease in manual data entry
- 95% process automation for routine tasks

**Timeline:**
- Ongoing throughout Q1
- Monthly reviews and adjustments

## Resource Allocation

- Product Innovation: 40% of resources
- Market Expansion: 35% of resources
- Operational Efficiency: 25% of resources

## Risk Mitigation

- Weekly leadership team check-ins
- Bi-weekly all-hands updates
- Agile sprint methodology for quick pivots
- Buffer time built into all timelines

This document demonstrates SuperAssistant's ability to handle strategic planning documents and provide context-aware assistance.
EOF

echo "✅ Created: /tmp/demo_documents/q1_strategic_priorities.txt"

echo ""
echo "📊 Demo Data Summary:"
echo "   - 4 test documents created in /tmp/demo_documents/"
echo "   - White rabbit document: For KB retrieval demo"
echo "   - General demo document: For standard upload testing"
echo "   - Performance test: For speed verification"
echo "   - Strategic priorities: For chat quality demo"
echo ""
echo "🎯 Next Steps:"
echo "   1. Start your backend server"
echo "   2. Upload these documents via UI or API"
echo "   3. Wait for processing to complete"
echo "   4. Run through DEMO_DAY_CHECKLIST.md"
echo ""
echo "✨ You're ready for tomorrow's demo!"
