"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

type Job = {
  id: string;
  status: "queued" | "running" | "done" | "error";
  progress: number;
  message: string;
  error: string | null;
  title: string;
  video_url: string | null;
};

type Lesson = { key: string; title: string };

const EXAMPLES = [
  "x² - 5x + 6 = 0",
  "2x² - 7x + 3 = 0",
  "2x + 5 = x + 9",
  "3(x - 2) = x + 8",
  "2x + 3y = 12; x - y = 1",
  "A car travels 150 km in 3 hours. Find its speed.",
];

const FALLBACK_LESSONS: Lesson[] = [
  { key: "trig_balloon", title: "Trigonometry: height of a balloon" },
  { key: "mirror_concave", title: "Concave mirror image formation" },
  { key: "mirror_convex", title: "Convex mirror image formation" },
  { key: "reflection", title: "Reflection of light" },
  { key: "covalent_bonds", title: "Covalent bonds" },
];

async function readError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    /* not JSON */
  }
  return "Something went wrong. Please try again.";
}

export default function Home() {
  const [text, setText] = useState(EXAMPLES[0]);
  const [lessons, setLessons] = useState<Lesson[]>(FALLBACK_LESSONS);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    fetch(`${API}/api/lessons`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((l: Lesson[]) => alive.current && l.length && setLessons(l))
      .catch(() => {});
    return () => {
      alive.current = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const poll = useCallback(async (id: string) => {
    const startedAt = Date.now();
    while (alive.current) {
      await new Promise<void>((resolve) => {
        timer.current = setTimeout(resolve, 1500);
      });
      if (!alive.current) return;
      try {
        const res = await fetch(`${API}/api/jobs/${id}`);
        if (!res.ok) throw new Error(await readError(res));
        const j: Job = await res.json();
        if (!alive.current) return;
        setJob(j);
        if (j.status === "done") return setBusy(false);
        if (j.status === "error") {
          setError(j.error ?? "The video could not be made.");
          return setBusy(false);
        }
        if (Date.now() - startedAt > 8 * 60 * 1000) throw new Error("This is taking too long. Please try again.");
      } catch (e) {
        if (!alive.current) return;
        setError(e instanceof Error ? e.message : "Network error. Is the server running?");
        return setBusy(false);
      }
    }
  }, []);

  const start = async (request: () => Promise<Response>) => {
    setError("");
    setJob(null);
    setBusy(true);
    try {
      const res = await request();
      if (!res.ok) throw new Error(await readError(res));
      const j: Job = await res.json();
      setJob(j);
      poll(j.id);
    } catch (e) {
      setError(e instanceof Error && e.message !== "Failed to fetch" ? e.message : "Cannot reach the video server. Please try again in a moment.");
      setBusy(false);
    }
  };

  const generate = (value: string) => {
    if (!value.trim()) return setError("Please type a problem first.");
    start(() =>
      fetch(`${API}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value }),
      }),
    );
  };

  const upload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    start(() => fetch(`${API}/api/jobs/upload`, { method: "POST", body: form }));
    if (fileRef.current) fileRef.current.value = "";
  };

  const videoSrc = job?.status === "done" && job.video_url ? `${API}${job.video_url}` : null;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10 sm:py-16">
      <header className="text-center">
        <h1 className="text-3xl font-bold sm:text-4xl">RN Classes Video Studio</h1>
        <p className="mt-2 text-slate-400">Type a problem or upload a photo and get a step-by-step video solution.</p>
      </header>

      <section className="rounded-xl bg-slate-800 p-5 shadow-xl">
        <label htmlFor="problem" className="mb-2 block text-sm font-semibold text-green-400">
          Type your problem
        </label>
        <textarea
          id="problem"
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={600}
          rows={3}
          placeholder="e.g. 2x² - 7x + 3 = 0"
          className="w-full resize-none rounded-lg border border-slate-600 bg-slate-700 p-3 text-white placeholder-slate-400 focus:border-blue-400 focus:outline-none"
        />
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setText(ex)}
              className="rounded-full border border-slate-600 px-3 py-1 text-xs text-slate-300 hover:border-blue-400 hover:text-white"
            >
              {ex}
            </button>
          ))}
        </div>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            disabled={busy}
            onClick={() => generate(text)}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-3 font-bold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Making your video…" : "Generate video"}
          </button>
          <label
            className={`flex-1 cursor-pointer rounded-lg border border-dashed border-slate-500 px-4 py-3 text-center text-sm text-slate-300 hover:border-blue-400 ${busy ? "pointer-events-none opacity-50" : ""}`}
          >
            Or upload a photo / PDF
            <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={upload} className="hidden" />
          </label>
        </div>
      </section>

      <section className="rounded-xl bg-slate-800 p-5 shadow-xl">
        <h2 className="mb-3 text-sm font-semibold text-purple-300">Ready-made lessons</h2>
        <div className="flex flex-wrap gap-2">
          {lessons.map((l) => (
            <button
              key={l.key}
              type="button"
              disabled={busy}
              onClick={() => generate(l.key)}
              className="rounded-lg bg-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-600 disabled:opacity-50"
            >
              {l.title}
            </button>
          ))}
        </div>
      </section>

      {busy && job && (
        <section aria-live="polite" className="rounded-xl bg-slate-800 p-5 shadow-xl">
          <p className="mb-2 text-sm text-slate-300">{job.message}</p>
          <div className="h-3 w-full overflow-hidden rounded-full bg-slate-700">
            <div className="h-full rounded-full bg-blue-500 transition-all duration-500" style={{ width: `${Math.max(job.progress, 4)}%` }} />
          </div>
          <p className="mt-2 text-xs text-slate-500">Most solutions take under a minute. Lessons with animation can take a couple of minutes.</p>
        </section>
      )}

      {error && (
        <p role="alert" className="rounded-xl border border-red-500/40 bg-red-950/40 p-4 text-red-300">
          {error}
        </p>
      )}

      {videoSrc && (
        <section className="rounded-xl bg-slate-800 p-3 shadow-xl">
          <video key={videoSrc} src={videoSrc} controls autoPlay playsInline className="w-full rounded-lg" />
          <div className="flex items-center justify-between p-2">
            <span className="text-sm text-slate-400">{job?.title}</span>
            <a href={videoSrc} download="rn-solution.mp4" className="text-sm font-semibold text-blue-400 hover:text-blue-300">
              Download video
            </a>
          </div>
        </section>
      )}
    </main>
  );
}
