#!/bin/bash

# Fix ChatInterface.tsx
FILE="components/ChatInterface.tsx"
if ! grep -q "import.*logger.*from.*@/lib/logger" "$FILE"; then
  sed -i '' "3i\\
import { logger } from '@/lib/logger';\\
" "$FILE"
fi

sed -i '' \
  -e "s/console\.log('Stream complete:', data\.tokens)/logger.debug('Stream complete', { tokens: data.tokens })/g" \
  -e "s/console\.log(\`Using \${data\.count} context chunks\`)/logger.debug('Using context chunks', { count: data.count })/g" \
  "$FILE"

# Fix IdeationVelocityCard.tsx
FILE="components/IdeationVelocityCard.tsx"
if ! grep -q "import.*logger.*from.*@/lib/logger" "$FILE"; then
  sed -i '' "3i\\
import { logger } from '@/lib/logger';\\
" "$FILE"
fi

sed -i '' \
  -e "s/console\.log('⚡ Ideation Velocity Response:', result);/logger.debug('Ideation Velocity Response', { result });/g" \
  "$FILE"

# Fix UsageAnalytics.tsx
FILE="components/UsageAnalytics.tsx"
if ! grep -q "import.*logger.*from.*@/lib/logger" "$FILE"; then
  sed -i '' "3i\\
import { logger } from '@/lib/logger';\\
" "$FILE"
fi

sed -i '' \
  -e "s/console\.log('📊 Usage Trends Response:', trendsData);/logger.debug('Usage Trends Response', { trendsData });/g" \
  -e "s/console\.log('👥 Active Users Response:', activeUsersData);/logger.debug('Active Users Response', { activeUsersData });/g" \
  -e "s/console\.log('📈 Data Check:', { hasTrends, hasActiveUsers, hasData, trendsLength: trends\.length, activeUsers });/logger.debug('Data Check', { hasTrends, hasActiveUsers, hasData, trendsLength: trends.length, activeUsers });/g" \
  "$FILE"

echo "Console.log statements replaced with logger calls"
