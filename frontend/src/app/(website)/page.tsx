import { DemoPlayer } from "@/components/website/DemoPlayer";
import { IntegrationGrid } from "@/components/website/IntegrationGrid";
import { PlatformFlow } from "@/components/website/PlatformFlow";
import { ScrollProgress } from "@/components/website/ScrollProgress";
import { SiteNav } from "@/components/website/SiteNav";
import { UseCases } from "@/components/website/UseCases";
import { DASHBOARD_ROOT } from "@/lib/paths";
import { FAQS } from "@/lib/website/content";

export default function WebsitePage() {
  return (
    <>
      <ScrollProgress />
      <SiteNav />
      <main id="top">
        <section className="hero">
          <div className="wrap hero-inner">
            <p className="eyebrow">AI voice agents for phone calls</p>
            <h1>
              AI agents that <span className="accent">answer, book and follow up</span> on every
              call.
            </h1>
            <p className="lede">
              Put an AI agent on your business number. It answers customers, books appointments and
              follows up on leads, then tells you how every call went.
            </p>
            <div className="hero-actions">
              <a className="button primary large" href="#demo">
                ▶ Watch it take a call
              </a>
            </div>
          </div>
        </section>

        <section id="demo" className="section demo-section">
          <div className="wrap">
            <DemoPlayer />
          </div>
        </section>

        <section id="use-cases" className="section">
          <div className="wrap">
            <p className="kicker">Use cases</p>
            <h2 className="section-title">One agent for every call your team makes</h2>
            <p className="section-lede">
              Each agent follows its own script, from booking a clinic visit to winning back an
              abandoned cart.
            </p>
            <UseCases />
          </div>
        </section>

        <section id="platform" className="section alt">
          <div className="wrap">
            <PlatformFlow />
          </div>
        </section>

        <section id="integrations" className="section">
          <div className="wrap">
            <p className="kicker">Integrations</p>
            <h2 className="section-title">Connects to the tools your team already uses</h2>
            <p className="section-lede">
              Turn an app on, paste its key, done. The agent books, looks things up and updates
              records while it talks, and every call&apos;s summary lands where your team works.
            </p>
            <IntegrationGrid />
          </div>
        </section>

        <section id="faq" className="section alt">
          <div className="wrap faq-wrap">
            <h2 className="section-title">Frequently asked questions</h2>
            <div className="faq">
              {FAQS.map(([question, answer], index) => (
                <details key={question} open={index === 0}>
                  <summary>{question}</summary>
                  <p>{answer}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="cta">
          <div className="wrap cta-inner">
            <h2>Hear it handle a real call</h2>
            <p>
              Watch a booking from the first hello to the confirmation, then explore the workspace
              behind it.
            </p>
            <div className="hero-actions">
              <a className="button inverse large" href="#demo">
                ▶ Watch the demo
              </a>
              <a className="button outline large" href={DASHBOARD_ROOT}>
                Try the demo workspace
              </a>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
