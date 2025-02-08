import Link from 'next/link';

const connections = [
  {
    name: 'Connect Gmail',
    description: 'Link your Gmail account to sync your emails.',
    href: '/connect-gmail',
    completed: false,
  },
  {
    name: 'Connect Google Calendar',
    description: 'Link your Google Calendar to sync your events.',
    href: '/connect-google-calendar',
    completed: true,
  },
  {
    name: 'Connect Notion',
    description: 'Link your Notion account to sync your notes.',
    href: '/connect-notion',
    completed: false,
  },
];

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      <h1 className="text-4xl font-bold mb-8">Connect Your Accounts</h1>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {connections.map((connection) => (
          <Link
            key={connection.name}
            href={connection.href}
            className={`block text-black p-6 max-w-sm bg-white rounded-lg border border-gray-200 shadow-md transition duration-300 
              ${connection.completed
                ? 'bg-green-100 hover:bg-green-200'
                : 'hover:bg-gray-100'
              }`}
          >
            <h2 className="text-2xl font-bold mb-2">
              {connection.completed && (
                <span className="mr-2">✓</span>
              )}
              {connection.name}
            </h2>
            <p className="text-gray-700">{connection.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
