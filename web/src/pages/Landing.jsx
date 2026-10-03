import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div className="page landing" id="main">
      <a className="skip-link" href="#intro">
        Skip to content
      </a>
      <p className="eyebrow">P42: decisions you can audit</p>
      <h1 className="hero-title" id="intro">Messy situations in. One checkable call out.</h1>
      <p className="lede">
        Get plans which specialist skills to run, executes one per source: a dispatch note,
        a phone photo, a PDF bulletin. Then it reconciles everything into a decision with
        its reasoning, its evidence, and its confidence attached. Every run is logged, and
        the duty officer gets the last word.
      </p>
      <div className="hero-cta">
        <Link className="button primary" to="/console">
          Open the console
        </Link>
        <Link className="button quiet" to="/runs">
          Browse past runs
        </Link>
      </div>

      <section aria-labelledby="how-heading">
        <p className="eyebrow" id="how-heading">
          How it works
        </p>
        <ol className="trace">
          <li>
            <span className="num" aria-hidden="true">
              1
            </span>
            <p className="skill">sources in</p>
            <p className="because">
              Text, images, and documents arrive as fragments. Nothing needs to agree with
              anything else first.
            </p>
          </li>
          <li>
            <span className="num" aria-hidden="true">
              2
            </span>
            <p className="skill">skills assigned</p>
            <p className="because">
              A planner assigns one skill per source. The skills extract facts, severity,
              and risk flags. They never decide.
            </p>
          </li>
          <li>
            <span className="num" aria-hidden="true">
              3
            </span>
            <p className="skill">one call out</p>
            <p className="because">
              One step decides and shows its work: the chain, the evidence, the rejected
              alternatives, and what would prove it wrong.
            </p>
          </li>
        </ol>
      </section>

      <section aria-labelledby="capable-heading">
        <p className="eyebrow" id="capable-heading">
          What it actually does
        </p>
        <ul className="capable">
          <li>
            <strong>Three skills, typed end to end.</strong> Document facts, image findings,
            and the decision itself are validated schemas, not prose. Malformed model output
            is retried, never silently accepted.
          </li>
          <li>
            <strong>An audit trail with verdicts.</strong> Every run is recorded with its
            reasoning chain, and the duty officer can accept or override it. The log keeps
            every version.
          </li>
          <li>
            <strong>Two engines, stated plainly.</strong> Gemini 2.0 Flash when a key is set,
            Vertex AI with a project set, deterministic heuristics otherwise. The screen
            always says which one ran.
          </li>
          <li>
            <strong>One container to deploy.</strong> The API serves the built interface, so
            Cloud Run gets a single image with a single cold start.
          </li>
        </ul>
      </section>

      <footer className="site-footer">
        <p>
          Built for HackSprint P42 by Team Zero. Prototype engine: heuristic rules until a
          Gemini key is set.
        </p>
      </footer>
    </div>
  )
}
