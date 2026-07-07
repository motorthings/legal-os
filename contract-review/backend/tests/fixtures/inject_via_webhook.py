#!/usr/bin/env python3
"""
Inject synthetic interview via webhook endpoint
Simulates ElevenLabs webhook callback for Charlie Motor interview
"""
import requests
import json
import sys

# Synthetic interview transcript messages
SYNTHETIC_MESSAGES = [
    {"role": "agent", "message": "Hello Charlie, my name is Solomon. I am your guide for creating your own SuperAssistant. I will try to make this as painless as possible. If possible, please find a quiet and comfortable place where you won't be disturbed. This should take us about 15-20 minutes. I'll be asking questions to understand you and your work. We'll cover everything from what you value, business models you like, and what challenges you're facing. This conversation will help to create an AI executive assistant that's truly personalized to you -- your leadership style and strategic priorities. I'll pause right here before continuing to see if you have any questions."},
    {"role": "user", "message": "No questions, sounds good. Let's do this."},
    {"role": "agent", "message": "Great! Charlie, there are no right or wrong answers. I'm simply here to understand you and how you operate at your best. We will lean into your expertise as a leader. And we will leverage my ability to find patterns, gaps, and opportunities. Think of this as a conversation with an executive coach. Also, everything you share is confidential. It will only be used to configure your assistant. Shall we begin?"},
    {"role": "user", "message": "Yes, let's go."},
    {"role": "agent", "message": "Perfect. Let's start with what's not working as well as you'd like. Every leader faces bottlenecks and friction points. Understanding yours will allow me to create an assistant to address your largest pain points. What tasks or decisions tend to pile up on your desk that you wish you could delegate or automate? In other words, what are the biggest bottlenecks in your current workflow?"},
    {"role": "user", "message": "Oh man, where do I start? The biggest thing is coordinating schedules and follow-ups across multiple projects. I'm constantly juggling between different clients, partners, and internal team meetings. It probably takes me 5-6 hours a week just managing my calendar and sending follow-up emails. It's incredibly tedious and repetitive, and I know it's not the best use of my time."},
    {"role": "agent", "message": "That's really helpful. So scheduling and follow-ups are eating up significant time. When you look at how you spend your time overall, what percentage would you estimate goes to strategic work versus operational or administrative tasks like those? And what would be your ideal split?"},
    {"role": "user", "message": "Right now I'd say I'm spending about 30% of my time on strategic work - like thinking about product direction, business development, long-term planning. The other 70% is just firefighting and administrative stuff. Ideally I'd flip that - maybe 70% strategic, 30% operational. But honestly, even getting to 50-50 would be a huge win."},
    {"role": "agent", "message": "That's a significant gap between current and ideal. Let me ask about decision-making. Think about a recent decision that took longer than it should have. What made it slow or difficult? Was it unclear priorities, too many options, missing information, conflicting stakeholder needs, or something else?"},
    {"role": "user", "message": "Good question. Just last week I was trying to decide whether to pursue a partnership with a larger company. The challenge was that I had too many competing inputs - my co-founder thought we should wait, our advisor thought we should go for it, and I was worried about losing focus on our core product. I spent probably 10 hours over 3 days going back and forth. What I really needed was a framework to evaluate it objectively against our strategic goals."},
    {"role": "agent", "message": "That's really insightful - decision-making friction from multiple perspectives and lack of clear evaluation framework. When it comes to communicating with your team or stakeholders, what do you find the most difficult? For example, giving feedback, delegating clearly, writing strategic documents, aligning people on priorities, or identifying people's skills for certain projects?"},
    {"role": "user", "message": "Definitely giving developmental feedback. I'm good at tactical feedback like 'this deliverable needs X, Y, Z.' But when it comes to coaching someone on their growth areas or having those bigger career conversations, I tend to procrastinate. I think I worry about coming across wrong or demotivating people. So those conversations take me hours to prepare for, and I know I'm probably overthinking it."},
    {"role": "agent", "message": "That's very honest, thank you. Last question in this section - if you could magically free up 10 hours per week, what would you focus that time on?"},
    {"role": "user", "message": "Definitely product strategy and customer research. I want to be talking to users more, understanding their problems deeply, and thinking about where we should take the product in the next 12-18 months. That's where I add the most value, but I'm constantly pulled away by operational fires."},
    {"role": "agent", "message": "Excellent. Now let's talk about what matters most to you. Every leader has core principles that guide how they make decisions and lead their team. Understanding your values will help your assistant give you advice that resonates with who you are. When you're making an important decision, what principles do you always come back to?"},
    {"role": "user", "message": "I'd say the big ones are: customer impact first, transparency with the team, and long-term thinking over short-term wins. I also really value efficiency - not in a cut-corners way, but in a 'let's not waste time on things that don't matter' way. And I guess authenticity - I want to build something that feels true to who we are, not just chasing trends."},
    {"role": "agent", "message": "Those are strong values. How would you describe your leadership style? Are you more of a visionary setting direction, an enabler removing blockers, a developer coaching others, an executor driving results, or an architect designing systems? You might be a combination - what feels most true?"},
    {"role": "user", "message": "I think I'm a mix of visionary and architect. I love thinking about the big picture and where we're going, but I also really enjoy designing the systems and processes to get there. I'm probably weaker on the developer/coaching side - that's something I know I need to work on."},
    {"role": "agent", "message": "That's great self-awareness. Our frustrations often reveal our values. What frustrates you most when you see it in your organization or your industry?"},
    {"role": "user", "message": "Honestly, it's when people talk in circles without making decisions. I see it in meetings all the time - we'll discuss something for 45 minutes, and at the end nobody's actually committed to a next step. It drives me crazy. I'd rather make a decision and adjust later than have endless debates. The other thing is when people aren't direct with feedback. Like, just tell me what's wrong so we can fix it."},
    {"role": "agent", "message": "Very clear. Now I'd like to understand what frameworks and tools you already use in your work. This will help your assistant speak your language and integrate with how you already think. Do you use any strategic frameworks or models in your work? For example, OKRs, SWOT Analysis, Eisenhower Matrix, ICE Scoring, North Star Metrics, Agile methodologies, or any proprietary frameworks?"},
    {"role": "user", "message": "We use OKRs quarterly, though honestly we're not great at reviewing them consistently. I personally like the Eisenhower Matrix for prioritization - I use that in my head a lot. And we're loosely agile in how we do sprints, though we're a small team so it's not super formal."},
    {"role": "agent", "message": "Good. When you're evaluating options or priorities, do you have a go-to method or mental model? Like weighted scorecards, pros/cons lists, first principles thinking, cost-benefit analysis, or gut instinct based on experience?"},
    {"role": "user", "message": "I usually do a quick pros/cons list to start, but then I try to think from first principles - like, what's actually most important here? What are we trying to achieve? I'm probably 60% analytical, 40% gut instinct. The instinct part has gotten better as I've gained experience."},
    {"role": "agent", "message": "That makes sense. What tools does your team use for project management, collaboration, or documentation?"},
    {"role": "user", "message": "We're mostly in Notion for documentation and project tracking. We use Slack for communication, Google Drive for files, and we're experimenting with Linear for engineering tasks. It's a bit scattered to be honest."},
    {"role": "agent", "message": "And when you need to access strategic documents - like project plans, frameworks, or key reference materials - where do you typically find them? Are they centralized in one place, or scattered across email, Slack, and multiple platforms?"},
    {"role": "user", "message": "Mostly in Notion, but honestly there's stuff in Google Drive, some in Slack threads, and a bunch in my personal notes that I haven't properly documented. I'd say 60% centralized in Notion, 40% scattered. It's something I know we need to improve."},
    {"role": "agent", "message": "That's helpful context. Let's talk about your team. Tell me about your team structure. Who reports directly to you, and what are their primary roles or areas of focus?"},
    {"role": "user", "message": "I have three direct reports: Sarah who leads product and design, Marcus who leads engineering, and Jenny who handles operations and customer success. Then I have a couple contractors who work on specific projects. So it's a pretty lean team - maybe 8 people total including contractors."},
    {"role": "agent", "message": "Got it. Thinking about your team members - who are your strongest performers, and what are they great at? Who is ready for more responsibility or stretch assignments? Are there skill gaps you're working to fill?"},
    {"role": "user", "message": "Sarah is incredibly strong - she could probably run product at a much larger company. Marcus is solid technically but still developing his leadership skills as the team grows. Jenny is great at execution but sometimes needs help thinking strategically. I think Sarah is ready for more ownership, and Marcus could use some coaching on delegation. We probably need to hire someone focused on business development soon."},
    {"role": "agent", "message": "Excellent. When you need to delegate something, how do you typically decide who should own it? Do you have a system, or is it more intuitive?"},
    {"role": "user", "message": "It's pretty intuitive. I usually think about who has capacity, who has the right skills, and who would benefit from the growth opportunity. I probably err on the side of taking things myself if I'm unsure, which I know isn't ideal."},
    {"role": "agent", "message": "What does good delegation look like to you? How do you balance empowering your team with maintaining oversight?"},
    {"role": "user", "message": "Good delegation means being clear about the outcome and constraints, but leaving the 'how' up to them. I want to give people autonomy but also be available if they need help. I probably check in too frequently honestly - I'm working on trusting more and not micromanaging."},
    {"role": "agent", "message": "That's great awareness. Now let's talk about your communication style. When you're writing to your team or stakeholders, how would you describe your style? For example, formal or conversational, concise or detailed, data-driven or narrative-driven, direct or diplomatic?"},
    {"role": "user", "message": "Definitely conversational and direct. I try to be concise but sometimes I over-explain if it's something important. I like to use data when I have it, but I also tell stories to make points land. With the team I'm very casual, with investors or partners I'm a bit more polished but still pretty direct."},
    {"role": "agent", "message": "Perfect. What types of documents or communications do you create most often? Strategic briefs, status updates, feedback conversations, emails to stakeholders, presentations?"},
    {"role": "user", "message": "Mostly status updates to investors and the board, strategic briefs when we're launching something new, and I probably should be doing more written feedback but I tend to do that verbally. Oh, and lots of partner outreach emails."},
    {"role": "agent", "message": "And do you communicate differently depending on your audience - like your team versus executive peers versus board or stakeholders versus clients?"},
    {"role": "user", "message": "Yeah, definitely. With the team I'm super casual and direct. With the board I'm more formal and focus on metrics and progress. With potential partners I'm more polished and emphasize our value prop. With customers I try to be empathetic and solution-focused."},
    {"role": "agent", "message": "Great. When you give feedback to your team, what's your approach? Are you more direct and candid, coaching and developmental, structured with frameworks, or conversational and relationship-focused?"},
    {"role": "user", "message": "I'm naturally direct, but I'm trying to be more developmental. I probably need more structure - like I should probably use frameworks like SBI but I usually just wing it. I want to get better at the coaching aspect."},
    {"role": "agent", "message": "Understood. As we wrap up, I want to understand what success looks like for you. How do you measure success in your role? What are the key outcomes or metrics that matter most to you?"},
    {"role": "user", "message": "The main things are: revenue growth, customer retention, and product-market fit indicators like usage and NPS. But also things like team satisfaction and my own ability to focus on strategic work versus being in the weeds. If we're growing sustainably and I'm not burnt out, that's success."},
    {"role": "agent", "message": "Excellent. What are your top 3 strategic priorities right now? If everything else fell away, what are the initiatives or goals that absolutely must succeed?"},
    {"role": "user", "message": "One, close our next round of funding in the next 3 months. Two, launch our V2 product by end of Q1. Three, get to 50 active customers by mid-year. Those are the must-wins."},
    {"role": "agent", "message": "Given those priorities, what kinds of requests or opportunities should you say yes to, and what should you say no to? Help me understand your filters."},
    {"role": "user", "message": "I should say yes to things that directly support funding, product development, or customer acquisition. I should say no to speaking opportunities, random networking requests, and shiny object partnerships that don't move those needles. The hard part is I'm tempted by interesting side projects that aren't actually priorities."},
    {"role": "agent", "message": "Last question - looking at the next 12-18 months, what do you want to get better at as a leader?"},
    {"role": "user", "message": "I want to get better at coaching my team and having those developmental conversations. I want to improve my strategic communication - like articulating vision in a way that gets people excited. And I want to get better at saying no and protecting my time for what actually matters."},
    {"role": "agent", "message": "This has been incredibly helpful, Charlie. Thank you for your openness and thoughtfulness. I have everything I need to create your personalized SuperAssistant. We'll process this conversation and generate your custom system instructions and function library. You should hear from our team within 24-48 hours with next steps. Is there anything else you'd like to add or any questions about the process?"},
    {"role": "user", "message": "No, this was great. Looking forward to seeing what you come up with."},
    {"role": "agent", "message": "Perfect. Thank you again, Charlie. Talk soon!"}
]

def inject_interview(backend_url):
    """Inject synthetic interview via webhook"""

    print("🎬 Injecting synthetic interview for Charlie Motor")
    print(f"   Backend: {backend_url}")
    print()

    # Construct webhook payload (mimicking ElevenLabs webhook format)
    payload = {
        "agent_id": "placeholder_agent_id",  # This will be replaced by actual agent_id from session
        "conversation_id": "synthetic_interview_charlie",
        "transcript": SYNTHETIC_MESSAGES
    }

    try:
        print("📤 Sending webhook request...")
        response = requests.post(
            f"{backend_url}/api/webhooks/interview-complete",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n✅ Interview injected successfully!")
            print()
            print("📊 Results:")
            print(f"   Extraction ID: {result.get('extraction_id', 'N/A')}")
            print(f"   Transcript Length: {result.get('transcript_length', 'N/A')} characters")
            print(f"   Message Count: {result.get('message_count', 'N/A')}")
            print(f"   Solomon Status: {result.get('solomon_status', 'N/A')}")
            print()
            print("🎯 Next Steps:")
            print("   1. Check the admin panel for extraction data")
            print("   2. Review TRIPS scores and extracted information")
            print("   3. Optionally run Solomon Stage 2 to generate system instructions")
            print("   4. Test chat interface with personalized assistant")
            return True
        else:
            print(f"\n❌ Webhook failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # Use Railway production backend
    backend_url = input("Enter backend URL (or press Enter for Railway production): ").strip()
    if not backend_url:
        backend_url = "https://superassistant-mvp-production.up.railway.app"

    print()
    result = inject_interview(backend_url)
    sys.exit(0 if result else 1)
