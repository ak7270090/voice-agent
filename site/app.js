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
];

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
      ["agent", "Dr. Priya Mehta is free on Wednesday at 11:00, 11:30, 12:00 and 1:30 pm. Which suits you?"],
      ["caller", "1:30 works."],
      ["agent", "Booked: Dr. Priya Mehta, Wednesday at 1:30 pm. You'll get a confirmation shortly. Anything else?"],
    ],
  },
  {
    industry: "E-commerce",
    tab: "Abandoned cart recovery",
    text: "Calls shoppers who left items in their cart and offers a reason to come back.",
    title: "Urban Threads",
    outcome: "Coupon accepted",
    lines: [
      ["agent", "Hi Neha, this is Urban Threads. You left the white sneakers in your cart. Can I help you finish the order?"],
      ["caller", "I was waiting to see if the price drops."],
      ["agent", "I can give you 10% off right now. Use code COMEBACK10 at checkout, valid until midnight."],
      ["caller", "Oh nice, I'll order tonight."],
      ["agent", "Great! The code is already on your account. Enjoy the sneakers."],
    ],
  },
  {
    industry: "E-commerce",
    tab: "Cash-on-delivery confirmation",
    text: "Confirms the order and address before it ships, so fewer parcels come back.",
    title: "QuickBasket",
    outcome: "Order confirmed",
    lines: [
      ["agent", "Hello Arjun, this is QuickBasket. You ordered a pressure cooker for ₹1,499, cash on delivery. Shall we ship it?"],
      ["caller", "Yes, please."],
      ["agent", "Is the address 14 MG Road, Pune still right?"],
      ["caller", "Yes, that's correct."],
      ["agent", "Done. It ships today and arrives by Friday. Thank you!"],
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
      ["agent", "What budget are you looking at, and when would you like to move?"],
      ["caller", "Around 80 lakh, in the next three months."],
      ["agent", "We have two projects that fit. Would Saturday at 11 am work for a site visit?"],
      ["caller", "Saturday works."],
    ],
  },
  {
    industry: "Financial services",
    tab: "Payment reminders",
    text: "Reminds customers of upcoming dues politely and records when they will pay.",
    title: "Apex Finance",
    outcome: "Payment date promised",
    lines: [
      ["agent", "Hello Meera, a quick reminder that your EMI of ₹8,200 is due on the 5th. Will you be able to pay on time?"],
      ["caller", "My salary comes on the 7th."],
      ["agent", "Understood. I've noted the 7th. Shall I send the payment link that morning?"],
      ["caller", "Yes, that helps."],
    ],
  },
  {
    industry: "Hospitality",
    tab: "Feedback after a stay",
    text: "Asks guests how it went, and passes unhappy ones straight to a manager.",
    title: "Bay View Hotel",
    outcome: "Rated 4 out of 5",
    lines: [
      ["agent", "Hi Sameer, thanks for staying at Bay View. How would you rate your stay out of 5?"],
      ["caller", "I'd say 4. The room was great, breakfast was a bit slow."],
      ["agent", "Thank you, I'll pass that on to the kitchen team. We hope to see you again!"],
    ],
  },
];

const STEPS = [
  {
    tab: "Build",
    title: "Design the conversation",
    points: [
      "Start from a template: booking, reminders, lead qualification",
      "Each step collects what it needs before moving on",
      "Connect a calendar so each doctor's real availability is used",
      "Publish when it's ready; every version is kept",
    ],
    image: "media/step-build.png",
  },
  {
    tab: "Test",
    title: "Talk to it before your callers do",
    points: [
      "Type or speak to the agent right inside the builder",
      "Watch the live step light up as the call moves",
      "Fix a step and try again in seconds",
    ],
    image: "media/step-test.png",
  },
  {
    tab: "Deploy",
    title: "Put it on a number or a list",
    points: [
      "Answer on your own numbers, or call out from them",
      "Run campaigns from a contact list with calling hours and retries",
      "Voicemail handled, and a person one step away",
    ],
    image: "media/step-deploy.png",
  },
  {
    tab: "Monitor",
    title: "See what happened on every call",
    points: [
      "Transcript, collected details and every action the agent took",
      "Summary, success and quality score after each call",
      "Cost per call, and what was sent to your other tools",
    ],
    image: "media/step-monitor.png",
  },
];

function setUpLinks() {
  const links = window.SHOWCASE ?? {};
  const targets = { console: links.consoleUrl, repository: links.repositoryUrl };
  document.querySelectorAll("[data-link]").forEach((anchor) => {
    const url = targets[anchor.dataset.link];
    if (url) {
      anchor.href = url;
      if (!url.startsWith("#")) anchor.target = "_blank";
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

function setUpSteps() {
  const root = document.querySelector("[data-steps]");
  const tabs = root.querySelector(".step-tabs");
  const heading = root.querySelector(".step-copy h3");
  const list = root.querySelector(".step-copy ul");
  const image = root.querySelector(".step-shot img");

  function show(index) {
    const step = STEPS[index];
    [...tabs.children].forEach((button, n) => button.setAttribute("aria-selected", String(n === index)));
    heading.textContent = step.title;
    list.replaceChildren(
      ...step.points.map((point) => Object.assign(document.createElement("li"), { textContent: point })),
    );
    image.src = step.image;
    image.alt = `${step.tab}: ${step.title}`;
  }

  STEPS.forEach((step, index) => {
    const button = document.createElement("button");
    button.role = "tab";
    button.innerHTML = `<span class="step-number">${index + 1}</span>`;
    button.append(step.tab);
    button.addEventListener("click", () => show(index));
    tabs.append(button);
  });
  show(0);
}

function setUpCases() {
  const root = document.querySelector("[data-cases]");
  const list = root.querySelector(".case-list");
  const title = root.querySelector(".chat-title");
  const outcome = root.querySelector(".chat-outcome");
  const lines = root.querySelector(".chat-lines");

  function show(index) {
    const useCase = USE_CASES[index];
    [...list.children].forEach((button, n) => button.setAttribute("aria-selected", String(n === index)));
    title.textContent = useCase.title;
    outcome.textContent = useCase.outcome;
    lines.replaceChildren(
      ...useCase.lines.map(([role, said]) => {
        const item = document.createElement("li");
        item.className = role;
        item.textContent = said;
        return item;
      }),
    );
  }

  USE_CASES.forEach((useCase, index) => {
    const button = document.createElement("button");
    button.role = "tab";
    button.innerHTML = '<em></em><strong></strong><span></span>';
    button.querySelector("em").textContent = useCase.industry;
    button.querySelector("strong").textContent = useCase.tab;
    button.querySelector("span").textContent = useCase.text;
    button.addEventListener("click", () => show(index));
    list.append(button);
  });
  show(0);
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
setUpCurrentSection();
setUpPlayer();
setUpCases();
setUpSteps();
