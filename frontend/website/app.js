// The demo player, the use-case conversations, the platform tabs, links from config.js and the
// current section in the navigation.

const DEMOS = [
  {
    id: "voice",
    tab: "Book an appointment",
    title: "Book an appointment over a call",
    text: "The caller asks for the skin doctor. The agent finds her free times, confirms the details and books the slot, all in one call.",
    video: "media/voice-call.mp4",
    poster: "media/voice-call.jpg",
  },
  {
    id: "phone",
    // Hidden until its recording is in media/.
    ready: false,
    tab: "Answer the phone",
    title: "Answers your business line",
    text: "A customer dials your number and the agent picks up straight away, day or night.",
    video: "media/phone-call.mp4",
    poster: "media/phone-call.jpg",
    // Optional: [{"at": seconds, "role": "agent" | "caller", "text": "..."}], highlighted in time.
    transcript: "media/phone-call.json",
  },
  {
    id: "campaign",
    tab: "Call a contact list",
    title: "Remind every patient in minutes",
    text: "Upload tomorrow's list and press start. Each person ends up confirmed, rescheduled, messaged on voicemail or called again later.",
    video: "media/campaign.mp4",
    poster: "media/campaign.jpg",
  },
  {
    id: "build",
    tab: "Build an agent",
    title: "Build an agent from scratch",
    text: "Give it a name and a job, draw the one step it needs, say how the call ends, then publish and test it.",
    video: "media/build-agent.mp4",
    poster: "media/build-agent.jpg",
  },
].filter((demo) => demo.ready !== false);

// Example conversations for the use-case section.
const USE_CASES = [
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
      ["agent", "Dr. Priya Mehta is free on Wednesday at 11:00, 11:30, 12:00 and 1:30. Which suits you?"],
      ["caller", "1:30 works."],
      ["agent", "To confirm: Rohan Gupta, 34, with Dr. Priya Mehta on Wednesday at 1:30. Is that right?"],
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
      ["agent", "Hi Neha, this is Urban Threads. You left the white sneakers in your cart. Is now a good time?"],
      ["caller", "Yes, go on."],
      ["agent", "Was anything holding you back from ordering?"],
      ["caller", "I was waiting to see if the price drops."],
      ["agent", "I can give you 10% off right now. Use code COMEBACK10 at checkout, valid until midnight."],
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
      ["agent", "Hello Arjun, this is QuickBasket. You ordered a pressure cooker for ₹1,500, cash on delivery. Shall we ship it?"],
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
      ["agent", "We have two ready-to-move projects that fit. Would Saturday at 11 am work for a site visit?"],
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
      ["agent", "Hello Meera, this is Apex Finance. Your EMI of ₹8,000 is due on the 5th. Will you be able to pay on time?"],
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

// The real templates (backend/studio-backend/.../agents/examples), drawn as the builder shows them.
const AFTER_THE_CALL = {
  kind: "after",
  name: "Saved and sent on",
  rows: [
    ["Saved", "Transcript, summary, success, cost"],
    ["Sent to", "Slack, HubSpot, Google Sheets"],
  ],
  why: "Every call is summarised and scored, then sent to the tools your team already uses.",
};

const FLOWS = [
  {
    tab: "Booking",
    demoPath: "/agents/4f0b424a-9c74-4312-9f34-e954e688cd54/flow",
    nodes: [
      {
        kind: "step",
        name: "Find out what the caller wants",
        says: "Welcome to City Hospital. How can I help you today?",
        moves: [
          ["Wants to book", "Collect booking details"],
          ["Has a question", "Answer questions"],
          ["Asks for a person", "Transfer to the front desk"],
        ],
        why: "The AI understands the caller and picks the next move, but only from the arrows you drew.",
      },
      {
        kind: "step",
        name: "Collect booking details",
        fields: ["Patient's name", "Age", "Doctor", "Day"],
        via: "all details collected",
        why: "The call moves on only when all four details are in. That's decided by code, not the AI.",
      },
      {
        kind: "tool",
        name: "Check free times",
        rows: [
          ["Kind", "Cal.com: free times"],
          ["Looks up", "{doctor} on {day}"],
        ],
        via: "free times found",
        why: "This runs by itself, so a time is never offered before it has been checked.",
      },
      {
        kind: "step",
        name: "Choose a free time",
        fields: ["Time, from the free times"],
        via: "the caller picks one",
        why: "Only the caller's own words can set the time. The AI can't choose one for them.",
      },
      {
        kind: "step",
        name: "Read back and confirm",
        says: "To confirm: {patient_name}, aged {patient_age}, with {doctor} on {day} at {time}. Is that right?",
        why: "The read-back is filled in by code, so a name or number is never misread.",
      },
      {
        kind: "tool",
        name: "Book the appointment",
        rows: [
          ["Kind", "Cal.com: booking"],
          ["Says", "One moment while I book that."],
        ],
        via: "a clear yes",
        why: "A plain yes starts the booking, and it only ever happens once, even if a request is retried.",
      },
      {
        branches: [
          {
            via: "booked",
            kind: "end",
            name: "Booked",
            says: "Your appointment with {doctor} is booked for {weekday} at {time}.",
          },
          {
            via: "slot just taken",
            kind: "step",
            name: "Choose a free time",
            says: "That time was just taken. Which other time suits you?",
            loopsBack: "Goes back and offers the new free times",
          },
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
        rows: [
          ["Contacts", "Your uploaded list"],
          ["Calling hours", "09:00 to 18:00"],
          ["Skips", "Anyone without consent"],
        ],
        why: "Upload a list and press start. Calls stay within your hours, with a limit on calls at once.",
      },
      {
        kind: "step",
        name: "Confirm the appointment",
        says: "Hello {name}, this is City Hospital calling about your appointment tomorrow.",
        via: "the person answers",
        why: "No answer means a retry later, and an answering machine gets a short message instead.",
      },
      {
        branches: [
          { via: "will come", kind: "end", name: "Confirmed", says: "Great, see you tomorrow. Goodbye." },
          {
            via: "wants another time",
            kind: "end",
            name: "Reschedule requested",
            says: "No problem. The front desk will call you to find a new time. Goodbye.",
          },
          {
            via: "says stop",
            kind: "end",
            name: "Opted out",
            says: "Understood, we won't call you again. Goodbye.",
          },
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
        says: "Hi, thanks for your interest. Do you have two minutes to talk about it?",
        fields: ["What they need", "Budget", "When they want to start"],
        why: "Each step collects only what it needs, and the agent asks for one detail at a time.",
      },
      {
        kind: "step",
        name: "Offer a meeting",
        fields: ["Meeting day"],
        via: "all details collected",
        why: "A lead that fits moves on by itself, with no script for the AI to lose track of.",
      },
      {
        branches: [
          {
            via: "picks a day",
            kind: "end",
            name: "Meeting requested",
            says: "Thanks. Our sales team will confirm the meeting for {meeting_day}.",
          },
          {
            via: "not interested",
            kind: "end",
            name: "Not interested",
            says: "Thanks for your time. Goodbye.",
          },
        ],
        why: "Both endings are recorded, so you can see how many leads turned into meetings.",
      },
      AFTER_THE_CALL,
    ],
  },
];

const NODE_KINDS = {
  step: { label: "Step", icon: "◆" },
  tool: { label: "Tool", icon: "⇄" },
  end: { label: "End", icon: "■" },
  campaign: { label: "Campaign", icon: "▶" },
  after: { label: "After the call", icon: "✓" },
};

const CALM = matchMedia("(prefers-reduced-motion: reduce)").matches;
const LINE_PAUSE_MIN_MS = 700;
const LINE_PAUSE_PER_CHAR_MS = 14;
const LINE_PAUSE_MAX_MS = 2000;

function setUpScrollProgress() {
  const bar = document.querySelector(".scroll-progress");
  const page = document.documentElement;
  let queued = false;

  function update() {
    queued = false;
    const range = page.scrollHeight - innerHeight;
    bar.style.transform = `scaleX(${range > 0 ? scrollY / range : 0})`;
  }

  function request() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(update);
  }

  addEventListener("scroll", request, { passive: true });
  addEventListener("resize", request);
  update();
}

// The integration cards rise in one after another, once. Cards already on screen stay put.
function setUpCardReveal() {
  const grid = document.querySelector(".app-grid");
  if (CALM || grid.getBoundingClientRect().top < innerHeight) return;
  [...grid.children].forEach((card, order) => card.style.setProperty("--order", order));
  grid.classList.add("waiting");
  const observer = new IntersectionObserver(
    ([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      grid.classList.replace("waiting", "rising");
    },
    { threshold: 0.2 },
  );
  observer.observe(grid);
}

// "Watch" buttons also start the video, not only scroll to it.
function setUpWatchButtons() {
  const video = document.querySelector(".player-video");
  document.querySelectorAll('a[href="#demo"]').forEach((button) => {
    button.addEventListener("click", () => video.play().catch(() => {}));
  });
}

function setUpLinks() {
  const links = window.SHOWCASE ?? {};
  const targets = { console: links.consoleUrl, repository: links.repositoryUrl };
  document.querySelectorAll("[data-link]").forEach((anchor) => {
    const url = targets[anchor.dataset.link];
    if (url) {
      anchor.href = url;
      if (url.startsWith("http")) anchor.target = "_blank";
    } else {
      anchor.hidden = true;
    }
  });
}

function setUpPlayer() {
  const root = document.querySelector("[data-player]");
  const tabs = root.querySelector(".player-tabs");
  const video = root.querySelector(".player-video");
  const missing = root.querySelector(".player-missing");
  const title = root.querySelector(".player-title");
  const text = root.querySelector(".player-text");
  const transcript = root.querySelector(".player-transcript");
  let lines = [];

  async function show(demo) {
    tabs.querySelectorAll("button").forEach((button) => {
      button.setAttribute("aria-selected", String(button.dataset.id === demo.id));
    });
    title.textContent = demo.title;
    text.textContent = demo.text;
    transcript.replaceChildren();
    lines = [];
    const exists = await fetch(demo.video, { method: "HEAD" }).then((r) => r.ok, () => false);
    video.hidden = !exists;
    missing.hidden = exists;
    if (!exists) {
      video.removeAttribute("src");
      missing.textContent = "This recording is coming soon.";
      return;
    }
    video.poster = demo.poster;
    video.src = demo.video;
    if (demo.transcript) {
      lines = await fetch(demo.transcript).then((r) => (r.ok ? r.json() : []), () => []);
      transcript.replaceChildren(
        ...lines.map((line) => {
          const item = document.createElement("li");
          item.dataset.role = line.role;
          item.innerHTML = `<span class="who"></span><span class="said"></span>`;
          item.querySelector(".who").textContent = line.role === "agent" ? "Agent" : "Caller";
          item.querySelector(".said").textContent = line.text;
          item.addEventListener("click", () => {
            video.currentTime = line.at;
            video.play();
          });
          return item;
        }),
      );
    }
  }

  video.addEventListener("timeupdate", () => {
    const items = transcript.children;
    let current = -1;
    lines.forEach((line, index) => {
      if (line.at <= video.currentTime) current = index;
    });
    [...items].forEach((item, index) => item.classList.toggle("now", index === current));
    items[current]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });

  DEMOS.forEach((demo) => {
    const button = document.createElement("button");
    button.role = "tab";
    button.dataset.id = demo.id;
    button.textContent = demo.tab;
    button.addEventListener("click", () => show(demo));
    tabs.append(button);
  });
  show(DEMOS[0]);
}

function element(tag, className, text) {
  const made = document.createElement(tag);
  if (className) made.className = className;
  if (text !== undefined) made.textContent = text;
  return made;
}

// {placeholders} look like what they are: values filled in during the call.
function withPlaceholders(text) {
  const line = element("p", "flow-says");
  text.split(/(\{\w+\})/).forEach((part) => {
    line.append(/^\{\w+\}$/.test(part) ? element("span", "flow-value", part.slice(1, -1).replace(/_/g, " ")) : part);
  });
  return line;
}

function flowCard(node, why) {
  const kind = NODE_KINDS[node.kind];
  const card = element("article", `flow-card ${node.kind}`);
  const head = element("div", "flow-card-head");
  head.append(element("span", "flow-kind", `${kind.icon} ${kind.label}`), element("h3", "", node.name));
  card.append(head);
  if (node.says) card.append(withPlaceholders(node.says));
  if (node.fields) {
    const fields = element("ul", "flow-fields");
    node.fields.forEach((field) => fields.append(element("li", "", field)));
    card.append(fields);
  }
  if (node.rows) {
    const rows = element("dl", "flow-rows");
    node.rows.forEach(([label, value]) => {
      const row = element("div");
      row.append(element("dt", "", label));
      const shown = element("dd");
      shown.append(...withPlaceholders(value).childNodes);
      row.append(shown);
      rows.append(row);
    });
    card.append(rows);
  }
  if (node.moves) {
    const moves = element("ul", "flow-moves");
    node.moves.forEach(([when, to]) => {
      const move = element("li");
      move.append(element("span", "", when), element("b", "", to));
      moves.append(move);
    });
    card.append(moves);
  }
  if (why) card.append(element("p", "flow-why", why));
  return card;
}

function setUpFlow() {
  const root = document.querySelector("[data-flow]");
  const tabs = root.querySelector(".flow-tabs");
  const canvas = root.querySelector(".flow-canvas");
  const noteTitle = root.querySelector(".flow-note strong");
  const noteText = root.querySelector(".flow-note p");
  const open = root.querySelector("[data-flow-open]");
  const consoleUrl = window.SHOWCASE?.consoleUrl;
  let stops = [];
  let queued = false;

  function highlight() {
    queued = false;
    // The card crossing the reading line, a little above the middle of the screen.
    const line = innerHeight * 0.45;
    const nearest = stops.reduce((best, stop) => {
      const box = stop.element.getBoundingClientRect();
      const distance = Math.abs((box.top + box.bottom) / 2 - line);
      return distance < best.distance ? { stop, distance } : best;
    }, { stop: stops[0], distance: Infinity }).stop;
    stops.forEach((stop) => stop.element.classList.toggle("active", stop === nearest));
    noteTitle.textContent = nearest.title;
    noteText.textContent = nearest.why;
  }

  function requestHighlight() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(highlight);
  }

  function show(index) {
    const flow = FLOWS[index];
    [...tabs.children].forEach((button, n) => button.setAttribute("aria-selected", String(n === index)));
    canvas.replaceChildren();
    canvas.scrollTop = 0;
    stops = [];
    flow.nodes.forEach((node, position) => {
      if (position > 0 && !node.branches) {
        const link = element("div", "flow-link");
        const label = flow.nodes[position - 1].via;
        if (label) link.append(element("span", "", label));
        canvas.append(link);
      }
      if (node.branches) {
        const link = element("div", "flow-link");
        const label = flow.nodes[position - 1].via;
        if (label) link.append(element("span", "", label));
        canvas.append(link);
        const split = element("div", "flow-branches");
        split.style.setProperty("--count", node.branches.length);
        node.branches.forEach((branch) => {
          const arm = element("div", "flow-arm");
          const wireIn = element("div", "arm-in");
          wireIn.append(element("span", "", branch.via));
          const card = flowCard(branch);
          arm.append(wireIn, card);
          // An arm that returns to an earlier step doesn't join the line going on.
          if (branch.loopsBack) {
            card.append(element("p", "flow-loop", `↩ ${branch.loopsBack}`));
          } else {
            arm.append(element("div", "arm-out"));
          }
          split.append(arm);
        });
        const why = element("p", "flow-why flow-branch-why", node.why);
        canvas.append(split, why);
        stops.push({ element: split, title: "Where the call can end up", why: node.why });
      } else {
        const card = flowCard(node, node.why);
        canvas.append(card);
        stops.push({ element: card, title: node.name, why: node.why });
      }
    });
    if (consoleUrl) {
      open.href = consoleUrl + flow.demoPath;
      open.textContent = flow.demoPath.endsWith("/flow") ? "Open this flow in the demo" : "Open the demo workspace";
    } else {
      open.hidden = true;
    }
    // Switching flows from further down starts the new one from its top.
    const top = root.getBoundingClientRect().top;
    if (top < 0) scrollBy({ top: top - 88, behavior: "instant" });
    highlight();
  }

  FLOWS.forEach((flow, index) => {
    const button = element("button", "", flow.tab);
    button.role = "tab";
    button.addEventListener("click", () => show(index));
    tabs.append(button);
  });
  addEventListener("scroll", requestHighlight, { passive: true });
  addEventListener("resize", requestHighlight);
  // On a phone the flow scrolls inside its own panel.
  canvas.addEventListener("scroll", requestHighlight, { passive: true });
  show(0);
}

function setUpCases() {
  const root = document.querySelector("[data-cases]");
  const list = root.querySelector(".case-list");
  const note = root.querySelector(".case-note");
  const stage = root.querySelector(".phone");
  const avatar = root.querySelector(".phone-avatar");
  const title = root.querySelector(".chat-title");
  const status = root.querySelector(".phone-status");
  const outcome = root.querySelector(".chat-outcome");
  const lines = root.querySelector(".chat-lines");
  let current = 0;
  let timer = null;
  let followingCall = true;

  function lineFor([role, said]) {
    const item = document.createElement("li");
    item.className = role;
    item.textContent = said;
    return item;
  }

  function finish(useCase) {
    stage.classList.add("ended");
    status.textContent = "Call ended";
    outcome.textContent = useCase.outcome;
  }

  // A pause as long as the last line takes to read, so the call has a natural pace.
  const pauseAfter = (said) => Math.min(LINE_PAUSE_MAX_MS, LINE_PAUSE_MIN_MS + said.length * LINE_PAUSE_PER_CHAR_MS);

  function play(useCase, shown = 0) {
    if (shown === useCase.lines.length) {
      finish(useCase);
      return;
    }
    const line = useCase.lines[shown];
    lines.append(lineFor(line));
    if (followingCall) lines.scrollTo({ top: lines.scrollHeight, behavior: "smooth" });
    timer = setTimeout(() => play(useCase, shown + 1), pauseAfter(line[1]));
  }

  function show(index, animate) {
    current = index;
    clearTimeout(timer);
    followingCall = true;
    const useCase = USE_CASES[index];
    [...list.children].forEach((button, n) => button.setAttribute("aria-selected", String(n === index)));
    note.textContent = useCase.text;
    avatar.textContent = useCase.title[0];
    title.textContent = useCase.title;
    stage.classList.remove("ended");
    status.textContent = "Live call";
    outcome.textContent = "";
    lines.replaceChildren();
    lines.scrollTop = 0;
    if (animate && !CALM) {
      play(useCase);
    } else if (CALM) {
      lines.append(...useCase.lines.map(lineFor));
      finish(useCase);
    }
  }

  // Reading back up the conversation stops it jumping down to each new line.
  ["wheel", "touchstart"].forEach((event) => {
    lines.addEventListener(event, () => { followingCall = false; }, { passive: true });
  });

  USE_CASES.forEach((useCase, index) => {
    const button = document.createElement("button");
    button.role = "tab";
    button.innerHTML = "<strong></strong><em></em><span></span>";
    button.querySelector("em").textContent = useCase.industry;
    button.querySelector("strong").textContent = useCase.tab;
    button.querySelector("span").textContent = useCase.text;
    button.addEventListener("click", () => {
      show(index, true);
      // On a phone the call sits below the list: bring it into view.
      if (matchMedia("(max-width: 900px)").matches) {
        stage.scrollIntoView({ block: "nearest", behavior: CALM ? "auto" : "smooth" });
      }
    });
    list.append(button);
  });
  show(0, false);
  // The first call starts when the section is reached, not while it is off screen.
  const observer = new IntersectionObserver(
    ([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      show(current, true);
    },
    { threshold: 0.35 },
  );
  if (!CALM) observer.observe(root);
}

function setUpCurrentSection() {
  const links = new Map(
    [...document.querySelectorAll(".nav-links a")].map((link) => [link.hash.slice(1), link]),
  );
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        links.forEach((link, id) => link.classList.toggle("current", id === entry.target.id));
      });
    },
    // A section counts as current while it crosses the band just below the navigation.
    { rootMargin: "-80px 0px -60% 0px" },
  );
  links.forEach((_, id) => {
    const section = document.getElementById(id);
    if (section) observer.observe(section);
  });
}

setUpLinks();
setUpWatchButtons();
setUpScrollProgress();
setUpCardReveal();
setUpCurrentSection();
setUpPlayer();
setUpCases();
setUpFlow();
