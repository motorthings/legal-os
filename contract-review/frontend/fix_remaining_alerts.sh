#!/bin/bash

# Fix app/admin/users/[userId]/page.tsx
FILE="app/admin/users/[userId]/page.tsx"
if ! grep -q "import toast from 'react-hot-toast'" "$FILE"; then
  sed -i '' "4i\\
import toast from 'react-hot-toast';\\
" "$FILE"
fi

sed -i '' \
  -e "s/alert(\`Interview scheduled! Session URL: \${data\.session_url}\`);/toast.success(\`Interview scheduled! Session URL: \${data.session_url}\`);/g" \
  -e "s/alert('Failed to schedule interview');/toast.error('Failed to schedule interview');/g" \
  -e "s/alert(\`Exported \${data\.export_metadata\.total_conversations} conversations with \${data\.export_metadata\.total_messages} messages\`);/toast.success(\`Exported \${data.export_metadata.total_conversations} conversations with \${data.export_metadata.total_messages} messages\`);/g" \
  -e "s/alert('Failed to export chat history');/toast.error('Failed to export chat history');/g" \
  "$FILE"

# Fix app/admin/documents/page.tsx
FILE="app/admin/documents/page.tsx"
if ! grep -q "import toast from 'react-hot-toast'" "$FILE"; then
  sed -i '' "4i\\
import toast from 'react-hot-toast';\\
" "$FILE"
fi

sed -i '' \
  -e "s/alert('Failed to delete document');/toast.error('Failed to delete document');/g" \
  -e "s/alert(\`Successfully deleted \${data\.deleted} document(s)\`);/toast.success(\`Successfully deleted \${data.deleted} document(s)\`);/g" \
  -e "s/alert('Failed to delete documents');/toast.error('Failed to delete documents');/g" \
  -e "s/alert('Failed to download document');/toast.error('Failed to download document');/g" \
  "$FILE"

echo "All remaining alerts fixed!"
