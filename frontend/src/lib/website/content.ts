// Everything the product page says and shows, kept apart from how it is drawn.
// The flows are the real templates (backend/studio-backend/.../agents/examples), drawn as the
// builder shows them: update them here when a template changes.

export type Demo = {
  id: string;
  ready?: boolean;
  tab: string;
  title: string;
  text: string;
  video: string;
  poster: string;
  transcript?: string;
};

export type UseCase = {
  industry: string;
  tab: string;
  text: string;
  title: string;
  outcome: string;
  lines: [role: string, said: string][];
};

export type NodeKind = "step" | "tool" | "end" | "campaign" | "after";

export type FlowBranch = {
  via: string;
  kind: NodeKind;
  name: string;
  loopsBack?: string;
};

export type FlowNode = {
  kind?: NodeKind;
  name?: string;
  says?: string;
  fields?: string[];
  detail?: string;
  via?: string;
  why: string;
  branches?: FlowBranch[];
};

export type Flow = {
  tab: string;
  demoPath: string;
  nodes: FlowNode[];
};

export type IntegrationApp = {
  name: string;
  text: string;
  color: string;
  wordmark: boolean;
  outline: boolean;
  paths: { d: string; fill?: string }[];
};

const ALL_DEMOS: Demo[] = [
  {
    id: "voice",
    tab: "Book an appointment",
    title: "Book an appointment over a call",
    text: "The caller asks for the skin doctor. The agent finds her free times, confirms the details and books the slot, all in one call.",
    video: "/media/voice-call.mp4",
    poster: "/media/voice-call.jpg",
  },
  {
    id: "phone",
    // Hidden until its recording is in media/.
    ready: false,
    tab: "Answer the phone",
    title: "Answers your business line",
    text: "A customer dials your number and the agent picks up straight away, day or night.",
    video: "/media/phone-call.mp4",
    poster: "/media/phone-call.jpg",
    // Optional: [{"at": seconds, "role": "agent" | "caller", "text": "..."}], highlighted in time.
    transcript: "/media/phone-call.json",
  },
  {
    id: "campaign",
    tab: "Call a contact list",
    title: "Remind every patient in minutes",
    text: "Upload tomorrow's list and press start. Each person ends up confirmed, rescheduled, messaged on voicemail or called again later.",
    video: "/media/campaign.mp4",
    poster: "/media/campaign.jpg",
  },
  {
    id: "build",
    tab: "Build an agent",
    title: "Build an agent from scratch",
    text: "Give it a name and a job, draw the one step it needs, say how the call ends, then publish and test it.",
    video: "/media/build-agent.mp4",
    poster: "/media/build-agent.jpg",
  },
];

// Tabs whose recording isn't in public/media yet stay hidden.
export const DEMOS = ALL_DEMOS.filter((demo) => demo.ready !== false);

export const USE_CASES: UseCase[] = [
  {
    industry: "Healthcare",
    tab: "Appointment booking",
    text: "Answers every call and books the right doctor at a free time.",
    title: "City Hospital",
    outcome: "Appointment booked",
    lines: [
      ["agent", "Welcome to City Hospital. How can I help you today?"],
      ["caller", "I'd like to see the skin doctor this Wednesday."],
      ["agent", "Sure. May I have the patient's full name?"],
      ["caller", "Rohan Gupta."],
      ["agent", "Thanks, Rohan. And your age?"],
      ["caller", "34."],
      [
        "agent",
        "Dr. Priya Mehta is free on Wednesday at 11:00, 11:30, 12:00 and 1:30. Which suits you?",
      ],
      ["caller", "1:30 works."],
      [
        "agent",
        "To confirm: Rohan Gupta, 34, with Dr. Priya Mehta on Wednesday at 1:30. Is that right?",
      ],
      ["caller", "Yes."],
      ["agent", "Booked. Your booking ID is A‑1002. Thank you for calling."],
    ],
  },
  {
    industry: "E-commerce",
    tab: "Abandoned cart recovery",
    text: "Calls shoppers who left items in their cart and offers a reason to come back.",
    title: "Urban Threads",
    outcome: "Coupon accepted",
    lines: [
      [
        "agent",
        "Hi Neha, this is Urban Threads. You left the white sneakers in your cart. Is now a good time?",
      ],
      ["caller", "Yes, go on."],
      ["agent", "Was anything holding you back from ordering?"],
      ["caller", "I was waiting to see if the price drops."],
      [
        "agent",
        "I can give you 10% off right now. Use code COMEBACK10 at checkout, valid until midnight.",
      ],
      ["caller", "Oh nice. Do you have them in size 7?"],
      ["agent", "Yes, size 7 is in stock, and delivery to your address takes two days."],
      ["caller", "Great, I'll order tonight."],
      ["agent", "I've sent the code by SMS. Enjoy the sneakers!"],
    ],
  },
  {
    industry: "E-commerce",
    tab: "Cash-on-delivery confirmation",
    text: "Confirms the order and address before it ships, so fewer parcels come back.",
    title: "QuickBasket",
    outcome: "Order confirmed",
    lines: [
      [
        "agent",
        "Hello Arjun, this is QuickBasket. You ordered a pressure cooker for ₹1,500, cash on delivery. Shall we ship it?",
      ],
      ["caller", "Yes, please."],
      ["agent", "Is the address 14 MG Road, Pune still right?"],
      ["caller", "It's flat 12, 14 MG Road."],
      ["agent", "Thanks, I've added flat 12. Will someone be home on Friday to pay?"],
      ["caller", "Yes, after 5 pm."],
      ["agent", "I've noted after 5 pm for the courier."],
      ["caller", "Perfect."],
      ["agent", "It ships today and arrives on Friday. Thank you, Arjun!"],
    ],
  },
  {
    industry: "Real estate",
    tab: "Lead qualification",
    text: "Calls every new enquiry within minutes, asks the right questions and books a visit.",
    title: "Skyline Homes",
    outcome: "Site visit booked",
    lines: [
      ["agent", "Hi Rahul, you asked about 2 BHK flats in Whitefield. Is this a good time?"],
      ["caller", "Yes, go ahead."],
      ["agent", "What budget are you looking at?"],
      ["caller", "Around 80 lakh."],
      ["agent", "And when would you like to move?"],
      ["caller", "In the next three months."],
      [
        "agent",
        "We have two ready-to-move projects that fit. Would Saturday at 11 am work for a site visit?",
      ],
      ["caller", "Saturday works."],
      ["agent", "Booked for Saturday at 11 am. I've sent the location by SMS. See you there!"],
    ],
  },
  {
    industry: "Financial services",
    tab: "Payment reminders",
    text: "Reminds customers of upcoming dues politely and records when they will pay.",
    title: "Apex Finance",
    outcome: "Payment date promised",
    lines: [
      [
        "agent",
        "Hello Meera, this is Apex Finance. Your EMI of ₹8,000 is due on the 5th. Will you be able to pay on time?",
      ],
      ["caller", "My salary comes on the 7th."],
      ["agent", "Understood. Can I note the 7th as your payment date?"],
      ["caller", "Yes, the 7th is fine."],
      ["agent", "Noted. Shall I send the payment link that morning?"],
      ["caller", "Yes, that helps."],
      ["agent", "I'll send it on the morning of the 7th. Thank you, Meera."],
    ],
  },
  {
    industry: "Hospitality",
    tab: "Feedback after a stay",
    text: "Asks guests how it went, and passes unhappy ones straight to a manager.",
    title: "Bay View Hotel",
    outcome: "Rated 4 out of 5",
    lines: [
      ["agent", "Hi Sameer, thanks for staying at Bay View. Do you have a minute for feedback?"],
      ["caller", "Sure."],
      ["agent", "How would you rate your stay out of 5?"],
      ["caller", "I'd say 4."],
      ["agent", "Thank you. What could we have done better?"],
      ["caller", "The room was great, breakfast was a bit slow."],
      ["agent", "I'll pass that on to the kitchen team. We hope to see you again!"],
    ],
  },
];

const AFTER_THE_CALL: FlowNode = {
  kind: "after",
  name: "Saved and sent on",
  detail: "Slack, HubSpot, Google Sheets",
  why: "Every call is summarised and scored, then sent to the tools your team already uses.",
};

export const FLOWS: Flow[] = [
  {
    tab: "Booking",
    demoPath: "/agents/4f0b424a-9c74-4312-9f34-e954e688cd54/flow",
    nodes: [
      {
        kind: "step",
        name: "Find out what the caller wants",
        says: "How can I help you today?",
        via: "wants to book",
        why: "The AI understands the caller and picks the next move, but only from the arrows you drew.",
      },
      {
        kind: "step",
        name: "Collect booking details",
        fields: ["Name", "Age", "Doctor", "Day"],
        via: "all details in",
        why: "The call moves on only when all four details are in. That's decided by code, not the AI.",
      },
      {
        kind: "tool",
        name: "Check free times",
        detail: "Cal.com",
        via: "times found",
        why: "This runs by itself, so a time is never offered before it has been checked.",
      },
      {
        kind: "step",
        name: "Choose a free time",
        fields: ["Time"],
        via: "caller picks one",
        why: "Only the caller's own words can set the time. The AI can't choose one for them.",
      },
      {
        kind: "step",
        name: "Read back and confirm",
        says: "{doctor} on {day} at {time}. Is that right?",
        via: "a clear yes",
        why: "The read-back is filled in by code, so a name or number is never misread.",
      },
      {
        kind: "tool",
        name: "Book the appointment",
        detail: "Cal.com",
        why: "A plain yes starts the booking, and it only ever happens once, even if a request is retried.",
      },
      {
        branches: [
          { via: "booked", kind: "end", name: "Booked" },
          { via: "slot taken", kind: "step", name: "Choose again", loopsBack: "Goes back" },
        ],
        why: "If someone took the slot first, the call goes back and offers the new free times.",
      },
      AFTER_THE_CALL,
    ],
  },
  {
    tab: "Reminders",
    demoPath: "/agents/3041d145-2b80-4aaf-8aec-3e6196442787/flow",
    nodes: [
      {
        kind: "campaign",
        name: "Tomorrow's reminders",
        detail: "Your contact list, within calling hours",
        why: "Upload a list and press start. Calls stay within your hours, with a limit on calls at once.",
      },
      {
        kind: "step",
        name: "Confirm the appointment",
        says: "Hello {name}, about your appointment tomorrow.",
        why: "No answer means a retry later, and an answering machine gets a short message instead.",
      },
      {
        branches: [
          { via: "will come", kind: "end", name: "Confirmed" },
          { via: "other time", kind: "end", name: "Moved" },
          { via: "says stop", kind: "end", name: "Opted out" },
        ],
        why: "Every call ends with a clear outcome. Anyone who says stop is never called again.",
      },
      AFTER_THE_CALL,
    ],
  },
  {
    tab: "Leads",
    demoPath: "/agents",
    nodes: [
      {
        kind: "step",
        name: "Qualify the lead",
        fields: ["Need", "Budget", "Timeline"],
        via: "all details in",
        why: "Each step collects only what it needs, and the agent asks for one detail at a time.",
      },
      {
        kind: "step",
        name: "Offer a meeting",
        fields: ["Meeting day"],
        why: "A lead that fits moves on by itself, with no script for the AI to lose track of.",
      },
      {
        branches: [
          { via: "picks a day", kind: "end", name: "Meeting" },
          { via: "says no", kind: "end", name: "Not interested" },
        ],
        why: "Both endings are recorded, so you can see how many leads turned into meetings.",
      },
      AFTER_THE_CALL,
    ],
  },
];

export const NODE_KINDS: Record<NodeKind, { label: string; icon: string }> = {
  step: { label: "Step", icon: "◆" },
  tool: { label: "Tool", icon: "⇄" },
  end: { label: "End", icon: "■" },
  campaign: { label: "Campaign", icon: "▶" },
  after: { label: "After the call", icon: "✓" },
};

export const FAQS: [question: string, answer: string][] = [
  [
    "What is an AI voice agent?",
    "A virtual team member that talks on the phone. It understands what callers say, answers in a natural voice, and gets things done, such as booking an appointment or confirming an order, without anyone on your team picking up.",
  ],
  [
    "How does a call work?",
    "The caller speaks, the agent understands the request, follows the script you designed, checks your calendar or systems where needed, and replies. When the call ends you get a summary, the outcome and the details it collected.",
  ],
  [
    "How long does it take to set up?",
    "Minutes for a first version. Start from a template, change what it says, test it by talking to it, and put it live when you are happy.",
  ],
  [
    "Will callers know they are talking to an AI?",
    "It sounds natural and handles interruptions, and you decide how it introduces itself: you can say so in the greeting. Callers can always ask for a person.",
  ],
  [
    "What happens when it doesn't know the answer?",
    "It says so instead of guessing, and offers to connect the caller to your team or have someone call back.",
  ],
  [
    "Can it call customers, not just answer calls?",
    "Yes. Upload a contact list and it calls each person within your calling hours, with details such as their name or order, and tries again if nobody answers.",
  ],
  [
    "Can we keep our existing phone number?",
    "Yes. Customers keep calling the number they know, and outgoing calls show it too. You can also start with a new number.",
  ],
  [
    "Does it work with our calendar and CRM?",
    "Yes. It books into your calendar during the call, and sends every call's summary to your CRM, Slack, a spreadsheet or any app you use.",
  ],
  [
    "How do we know how the calls went?",
    "Every call is listed with its transcript, outcome, summary and cost, and a dashboard shows trends across all your agents.",
  ],
  [
    "Is our data safe?",
    "Calls and transcripts stay in your account, and the logins it uses for your other tools are stored encrypted.",
  ],
];

export const APPS: IntegrationApp[] = [
  {
    name: "Cal.com",
    text: "Calendar and bookings",
    color: "#292929",
    wordmark: true,
    outline: false,
    paths: [
      {
        d: "M2.408 14.488C1.035 14.488 0 13.4 0 12.058c0-1.346.982-2.443 2.408-2.443.758 0 1.282.233 1.691.765l-.66.55a1.343 1.343 0 0 0-1.03-.442c-.93 0-1.44.711-1.44 1.57 0 .86.559 1.557 1.44 1.557.413 0 .765-.147 1.043-.443l.651.573c-.391.51-.929.743-1.695.743zM6.948 10.913h.89v3.49h-.89v-.51c-.185.362-.493.604-1.083.604-.943 0-1.695-.82-1.695-1.826 0-1.007.752-1.825 1.695-1.825.585 0 .898.241 1.083.604zm.026 1.758c0-.546-.374-.998-.964-.998-.568 0-.938.457-.938.998 0 .528.37.998.938.998.586 0 .964-.456.964-.998zM8.467 9.503h.89v4.895h-.89zM9.752 13.937a.53.53 0 0 1 .542-.528c.313 0 .533.242.533.528a.527.527 0 0 1-.533.537.534.534 0 0 1-.542-.537zM14.23 13.839c-.33.403-.832.658-1.426.658a1.806 1.806 0 0 1-1.84-1.826c0-1.007.778-1.825 1.84-1.825.572 0 1.07.241 1.4.622l-.687.577c-.172-.215-.396-.376-.713-.376-.568 0-.938.456-.938.998 0 .541.37.997.938.997.343 0 .58-.179.757-.42zM14.305 12.671c0-1.007.78-1.825 1.84-1.825 1.061 0 1.84.818 1.84 1.825 0 1.007-.779 1.826-1.84 1.826-1.06-.005-1.84-.82-1.84-1.826zm2.778 0c0-.546-.37-.998-.938-.998-.568-.004-.937.452-.937.998 0 .542.37.998.937.998.568 0 .938-.456.938-.998zM24 12.269v2.13h-.89v-1.911c0-.604-.281-.864-.704-.864-.396 0-.678.197-.678.864v1.91h-.89v-1.91c0-.604-.285-.864-.704-.864-.396 0-.744.197-.744.864v1.91h-.89v-3.49h.89v.484c.185-.376.52-.564 1.035-.564.489 0 .898.241 1.123.649.224-.417.554-.65 1.153-.65.731.005 1.299.56 1.299 1.442z",
      },
    ],
  },
  {
    name: "HubSpot",
    text: "CRM contacts and notes",
    color: "#ff7a59",
    wordmark: false,
    outline: false,
    paths: [
      {
        d: "M18.164 7.93V5.084a2.198 2.198 0 001.267-1.978v-.067A2.2 2.2 0 0017.238.845h-.067a2.2 2.2 0 00-2.193 2.193v.067a2.196 2.196 0 001.252 1.973l.013.006v2.852a6.22 6.22 0 00-2.969 1.31l.012-.01-7.828-6.095A2.497 2.497 0 104.3 4.656l-.012.006 7.697 5.991a6.176 6.176 0 00-1.038 3.446c0 1.343.425 2.588 1.147 3.607l-.013-.02-2.342 2.343a1.968 1.968 0 00-.58-.095h-.002a2.033 2.033 0 102.033 2.033 1.978 1.978 0 00-.1-.595l.005.014 2.317-2.317a6.247 6.247 0 104.782-11.134l-.036-.005zm-.964 9.378a3.206 3.206 0 113.215-3.207v.002a3.206 3.206 0 01-3.207 3.207z",
      },
    ],
  },
  {
    name: "Slack",
    text: "Call alerts for your team",
    color: "#4a154b",
    wordmark: false,
    outline: false,
    paths: [
      {
        d: "M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52z",
        fill: "#e01e5a",
      },
      {
        d: "M6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z",
        fill: "#e01e5a",
      },
      {
        d: "M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834z",
        fill: "#36c5f0",
      },
      {
        d: "M8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z",
        fill: "#36c5f0",
      },
      {
        d: "M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834z",
        fill: "#2eb67d",
      },
      {
        d: "M17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z",
        fill: "#2eb67d",
      },
      {
        d: "M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52z",
        fill: "#ecb22e",
      },
      {
        d: "M15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z",
        fill: "#ecb22e",
      },
    ],
  },
  {
    name: "Google Sheets",
    text: "A row for every call",
    color: "#34a853",
    wordmark: false,
    outline: false,
    paths: [
      {
        d: "M11.318 12.545H7.91v-1.909h3.41v1.91zM14.728 0v6h6l-6-6zm1.363 10.636h-3.41v1.91h3.41v-1.91zm0 3.273h-3.41v1.91h3.41v-1.91zM20.727 6.5v15.864c0 .904-.732 1.636-1.636 1.636H4.909a1.636 1.636 0 0 1-1.636-1.636V1.636C3.273.732 4.005 0 4.909 0h9.318v6.5h6.5zm-3.273 2.773H6.545v7.909h10.91v-7.91zm-6.136 4.636H7.91v1.91h3.41v-1.91z",
      },
    ],
  },
  {
    name: "Zapier",
    text: "Thousands of apps, no code",
    color: "#ff4f00",
    wordmark: false,
    outline: false,
    paths: [
      {
        d: "M4.157 0A4.151 4.151 0 0 0 0 4.161v15.678A4.151 4.151 0 0 0 4.157 24h15.682A4.152 4.152 0 0 0 24 19.839V4.161A4.152 4.152 0 0 0 19.839 0H4.157Zm10.61 8.761h.03a.577.577 0 0 1 .23.038.585.585 0 0 1 .201.124.63.63 0 0 1 .162.431.612.612 0 0 1-.162.435.58.58 0 0 1-.201.128.58.58 0 0 1-.23.042.529.529 0 0 1-.235-.042.585.585 0 0 1-.332-.328.559.559 0 0 1-.038-.235.613.613 0 0 1 .17-.431.59.59 0 0 1 .405-.162Zm2.853 1.572c.03.004.061.004.095.004.325-.011.646.064.937.219.238.144.431.355.552.609.128.279.189.582.185.888v.193a2 2 0 0 1 0 .219h-2.498c.003.227.075.45.204.642a.78.78 0 0 0 .646.265.714.714 0 0 0 .484-.136.642.642 0 0 0 .23-.318l.915.257a1.398 1.398 0 0 1-.28.537c-.14.159-.321.284-.521.355a2.234 2.234 0 0 1-.836.136 1.923 1.923 0 0 1-1.001-.245 1.618 1.618 0 0 1-.665-.703 2.221 2.221 0 0 1-.227-1.036 1.95 1.95 0 0 1 .48-1.398 1.9 1.9 0 0 1 1.3-.488Zm-9.607.023c.162.004.325.026.48.079.207.065.4.174.563.314.26.302.393.692.366 1.088v2.276H8.53l-.109-.711h-.065c-.064.163-.155.31-.272.439a1.122 1.122 0 0 1-.374.264 1.023 1.023 0 0 1-.453.083 1.334 1.334 0 0 1-.866-.264.965.965 0 0 1-.329-.801.993.993 0 0 1 .076-.431 1.02 1.02 0 0 1 .242-.363 1.478 1.478 0 0 1 1.043-.303h.952v-.181a.696.696 0 0 0-.136-.454.553.553 0 0 0-.438-.154.695.695 0 0 0-.378.086.48.48 0 0 0-.193.254l-.99-.144a1.26 1.26 0 0 1 .257-.563c.14-.174.321-.302.533-.378.261-.091.54-.136.82-.129.053-.003.106-.007.163-.007Zm4.384.007c.174 0 .347.038.506.114.182.083.34.211.458.374.257.423.377.911.351 1.406a2.53 2.53 0 0 1-.355 1.448 1.148 1.148 0 0 1-1.009.517c-.204 0-.401-.045-.582-.136a1.052 1.052 0 0 1-.48-.457 1.298 1.298 0 0 1-.114-.234h-.045l.004 1.784h-1.059v-4.713h.904l.117.805h.057c.068-.208.177-.401.328-.56a1.129 1.129 0 0 1 .843-.344h.076v-.004Zm7.559.084h.903l.113.805h.053a1.37 1.37 0 0 1 .235-.484.813.813 0 0 1 .313-.242.82.82 0 0 1 .39-.076h.234v1.051h-.401a.662.662 0 0 0-.313.008.623.623 0 0 0-.272.155.663.663 0 0 0-.174.26.683.683 0 0 0-.027.314v1.875h-1.054v-3.666Zm-17.515.003h3.262v.896L3.73 13.104l.034.113h1.973l.042.9H2.4v-.9l1.931-1.754-.045-.117H2.441v-.896Zm11.815 0h1.055v3.659h-1.055V10.45Zm3.443.684.019.016a.69.69 0 0 0-.351.045.756.756 0 0 0-.287.204c-.11.155-.174.336-.189.522h1.545c-.034-.526-.257-.787-.74-.787h.003Zm-5.718.163c-.026 0-.057 0-.083.004a.78.78 0 0 0-.31.053.746.746 0 0 0-.257.189 1.016 1.016 0 0 0-.204.695v.064c-.015.257.057.507.204.711a.634.634 0 0 0 .253.196.638.638 0 0 0 .314.061.644.644 0 0 0 .578-.265c.14-.223.204-.48.189-.74a1.216 1.216 0 0 0-.181-.711.677.677 0 0 0-.503-.257Zm-4.509 1.266a.464.464 0 0 0-.268.102.373.373 0 0 0-.114.276c0 .053.008.106.027.155a.375.375 0 0 0 .087.132.576.576 0 0 0 .397.11v.004a.863.863 0 0 0 .563-.182.573.573 0 0 0 .211-.457v-.14h-.903Z",
      },
    ],
  },
  {
    name: "n8n",
    text: "Automation workflows",
    color: "#ea4b71",
    wordmark: false,
    outline: false,
    paths: [
      {
        d: "M21.4737 5.6842c-1.1772 0-2.1663.8051-2.4468 1.8947h-2.8955c-1.235 0-2.289.893-2.492 2.111l-.1038.623a1.263 1.263 0 0 1-1.246 1.0555H11.289c-.2805-1.0896-1.2696-1.8947-2.4468-1.8947s-2.1663.8051-2.4467 1.8947H4.973c-.2805-1.0896-1.2696-1.8947-2.4468-1.8947C1.1311 9.4737 0 10.6047 0 12s1.131 2.5263 2.5263 2.5263c1.1772 0 2.1663-.8051 2.4468-1.8947h1.4223c.2804 1.0896 1.2696 1.8947 2.4467 1.8947 1.1772 0 2.1663-.8051 2.4468-1.8947h1.0008a1.263 1.263 0 0 1 1.2459 1.0555l.1038.623c.203 1.218 1.257 2.111 2.492 2.111h.3692c.2804 1.0895 1.2696 1.8947 2.4468 1.8947 1.3952 0 2.5263-1.131 2.5263-2.5263s-1.131-2.5263-2.5263-2.5263c-1.1772 0-2.1664.805-2.4468 1.8947h-.3692a1.263 1.263 0 0 1-1.246-1.0555l-.1037-.623A2.52 2.52 0 0 0 13.9607 12a2.52 2.52 0 0 0 .821-1.4794l.1038-.623a1.263 1.263 0 0 1 1.2459-1.0555h2.8955c.2805 1.0896 1.2696 1.8947 2.4468 1.8947 1.3952 0 2.5263-1.131 2.5263-2.5263s-1.131-2.5263-2.5263-2.5263m0 1.2632a1.263 1.263 0 0 1 1.2631 1.2631 1.263 1.263 0 0 1-1.2631 1.2632 1.263 1.263 0 0 1-1.2632-1.2632 1.263 1.263 0 0 1 1.2632-1.2631M2.5263 10.7368A1.263 1.263 0 0 1 3.7895 12a1.263 1.263 0 0 1-1.2632 1.2632A1.263 1.263 0 0 1 1.2632 12a1.263 1.263 0 0 1 1.2631-1.2632m6.3158 0A1.263 1.263 0 0 1 10.1053 12a1.263 1.263 0 0 1-1.2632 1.2632A1.263 1.263 0 0 1 7.579 12a1.263 1.263 0 0 1 1.2632-1.2632m10.1053 3.7895a1.263 1.263 0 0 1 1.2631 1.2632 1.263 1.263 0 0 1-1.2631 1.2631 1.263 1.263 0 0 1-1.2632-1.2631 1.263 1.263 0 0 1 1.2632-1.2632",
      },
    ],
  },
  {
    name: "Make",
    text: "Automation scenarios",
    color: "#6d00cc",
    wordmark: false,
    outline: false,
    paths: [
      {
        d: "M13.38 3.498c-.27 0-.511.19-.566.465L9.85 18.986a.578.578 0 0 0 .453.678l4.095.826a.58.58 0 0 0 .682-.455l2.963-15.021a.578.578 0 0 0-.453-.678l-4.096-.826a.589.589 0 0 0-.113-.012zm-5.876.098a.576.576 0 0 0-.516.318L.062 17.697a.575.575 0 0 0 .256.774l3.733 1.877a.578.578 0 0 0 .775-.258l6.926-13.781a.577.577 0 0 0-.256-.776L7.762 3.658a.571.571 0 0 0-.258-.062zm11.74.115a.576.576 0 0 0-.576.576v15.426c0 .318.258.578.576.578h4.178a.58.58 0 0 0 .578-.578V4.287a.578.578 0 0 0-.578-.576Z",
      },
    ],
  },
  {
    name: "Your own system",
    text: "Orders, stock, accounts",
    color: "#4f46e5",
    wordmark: false,
    outline: true,
    paths: [
      {
        d: "m16 18 6-6-6-6",
      },
      {
        d: "m8 6-6 6 6 6",
      },
    ],
  },
];
