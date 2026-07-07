import { render, screen } from '@testing-library/react'
import ChatMessage from '@/components/ChatMessage'

describe('ChatMessage', () => {
  it('renders user message with blue background', () => {
    const { container } = render(
      <ChatMessage
        content="Hello from user"
        role="user"
        timestamp="2025-10-31T12:00:00.000Z"
      />
    )

    const messageElement = screen.getByText('Hello from user')
    expect(messageElement).toBeInTheDocument()

    // Find the div with blue background (it's the second div in the hierarchy)
    const blueDivs = container.querySelectorAll('.bg-blue-500')
    expect(blueDivs.length).toBeGreaterThan(0)
    expect(blueDivs[0]).toHaveClass('text-white')
  })

  it('renders assistant message with gray background', () => {
    const { container } = render(
      <ChatMessage
        content="Hello from assistant"
        role="assistant"
        timestamp="2025-10-31T12:00:00.000Z"
      />
    )

    const messageElement = screen.getByText('Hello from assistant')
    expect(messageElement).toBeInTheDocument()

    // Find the div with gray background
    const grayDivs = container.querySelectorAll('.bg-gray-200')
    expect(grayDivs.length).toBeGreaterThan(0)
    expect(grayDivs[0]).toHaveClass('text-gray-900')
  })

  it('displays timestamp', () => {
    const timestamp = '2025-10-31T15:30:00.000Z'
    render(
      <ChatMessage
        content="Test message"
        role="user"
        timestamp={timestamp}
      />
    )

    // Timestamp should be formatted and displayed
    const timestampElement = screen.getByTitle(timestamp)
    expect(timestampElement).toBeInTheDocument()
  })

  it('aligns user messages to the right', () => {
    const { container } = render(
      <ChatMessage
        content="User message"
        role="user"
        timestamp="2025-10-31T12:00:00.000Z"
      />
    )

    const outerDiv = container.firstChild as HTMLElement
    expect(outerDiv).toHaveClass('justify-end')
  })

  it('aligns assistant messages to the left', () => {
    const { container } = render(
      <ChatMessage
        content="Assistant message"
        role="assistant"
        timestamp="2025-10-31T12:00:00.000Z"
      />
    )

    const outerDiv = container.firstChild as HTMLElement
    expect(outerDiv).toHaveClass('justify-start')
  })
})
