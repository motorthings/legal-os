#!/bin/bash

# Fix alert() calls in all files

# app/admin/conversations/[id]/page.tsx
if ! grep -q "import toast from 'react-hot-toast'" app/admin/conversations/[id]/page.tsx; then
  sed -i '' "4i\\
import toast from 'react-hot-toast';\\
" app/admin/conversations/[id]/page.tsx
fi

sed -i '' \
  -e "s/alert(data\.message || 'Conversation deleted successfully');/toast.success(data.message || 'Conversation deleted successfully');/g" \
  -e "s/alert(error instanceof Error ? error\.message : 'Failed to delete conversation');/toast.error(error instanceof Error ? error.message : 'Failed to delete conversation');/g" \
  app/admin/conversations/[id]/page.tsx

# app/admin/conversations/page.tsx
if ! grep -q "import toast from 'react-hot-toast'" app/admin/conversations/page.tsx; then
  sed -i '' "4i\\
import toast from 'react-hot-toast';\\
" app/admin/conversations/page.tsx
fi

sed -i '' \
  -e "s/alert(err instanceof Error ? err\.message : 'Failed to export conversation');/toast.error(err instanceof Error ? err.message : 'Failed to export conversation');/g" \
  app/admin/conversations/page.tsx

# app/admin/users/page.tsx
if ! grep -q "import toast from 'react-hot-toast'" app/admin/users/page.tsx; then
  sed -i '' "4i\\
import toast from 'react-hot-toast';\\
" app/admin/users/page.tsx
fi

sed -i '' \
  -e "s/alert('User created successfully! Invitation email sent\.');/toast.success('User created successfully! Invitation email sent.');/g" \
  app/admin/users/page.tsx

echo "Alert() calls replaced with toast notifications"
