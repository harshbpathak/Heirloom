import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import type { AskAnswer } from '../api';
import { api } from '../api';

interface ChatEntry {
  question: string;
  answer?: AskAnswer;
  error?: string;
}

/** Ask Heirloom (spec F8): chat-style Q&A with citations. */
export function AskPage() {
  const { repoId = '' } = useParams();
  const [question, setQuestion] = useState('');
  const [history, setHistory] = useState<ChatEntry[]>([]);

  const ask = useMutation({
    mutationFn: (q: string) => api.ask(repoId, q),
    onSuccess: (answer, q) =>
      setHistory((h) => h.map((e) => (e.question === q && !e.answer ? { ...e, answer } : e))),
    onError: (err, q) =>
      setHistory((h) =>
        h.map((e) => (e.question === q && !e.answer ? { ...e, error: (err as Error).message } : e)),
      ),
  });

  const submit = () => {
    const q = question.trim();
    if (!q) return;
    setHistory((h) => [...h, { question: q }]);
    ask.mutate(q);
    setQuestion('');
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-xl font-bold">Ask Heirloom</h1>
      <p className="text-sm text-gray-500">
        Try: “Why do we use Redis for sessions?” · “Who knows the billing module?” · “What breaks
        if I change utils/date.ts?”
      </p>

      <div className="space-y-3" aria-live="polite">
        {history.map((entry, i) => (
          <div key={i} className="space-y-2">
            <p className="ml-auto w-fit max-w-[85%] rounded-lg bg-blue-600 px-3 py-2 text-white">
              {entry.question}
            </p>
            {entry.answer ? (
              <div className="w-fit max-w-[85%] rounded-lg bg-gray-100 px-3 py-2 dark:bg-gray-800">
                <p className="whitespace-pre-wrap text-sm">{entry.answer.answer}</p>
                {entry.answer.citations.length > 0 && (
                  <p className="mt-1 text-xs text-gray-500">
                    Citations:{' '}
                    {entry.answer.citations.map((c, j) => (
                      <span key={c}>
                        {j > 0 && ', '}
                        <Link
                          className="underline"
                          to={`/repo/${repoId}/decisions?id=${c}`}
                          title={`Decision ${c}`}
                        >
                          [{c}]
                        </Link>
                      </span>
                    ))}
                  </p>
                )}
                <p className="mt-1 text-xs text-gray-400">route: {entry.answer.route}</p>
              </div>
            ) : entry.error ? (
              <p role="alert" className="text-sm text-red-600">
                {entry.error}
              </p>
            ) : (
              <p className="text-sm text-gray-500">Thinking…</p>
            )}
          </div>
        ))}
      </div>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label htmlFor="question" className="sr-only">
          Your question
        </label>
        <input
          id="question"
          className="input flex-1"
          placeholder="Ask about this repo…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button className="btn" type="submit" disabled={ask.isPending}>
          Ask
        </button>
      </form>
    </div>
  );
}
