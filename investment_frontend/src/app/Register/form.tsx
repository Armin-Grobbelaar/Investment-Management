'use client';

import { FormEvent } from 'react';

export default function Form() {
  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const response = await fetch(`http://localhost:8000/add_user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: formData.get('username'),
        email: formData.get('email'),
        password: formData.get('password'),
        full_name: formData.get('full_name'),
      }),
    });
    if (response.ok) {
        alert('User registered successfully');
    } else {
        alert('Registration failed');
    }
  };
  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-2 mx-auto max-w-md mt-10"
    >
      <input
        name="username"
        className="border border-black text-black"
        type="text"
        placeholder="Username"
      />
      <input
        name="email"
        className="border border-black text-black"
        type="email"
        placeholder="Email"
      />
      <input
        name="full_name"
        className="border border-black text-black"
        type="text"
        placeholder="Full Name"
      />
      <input
        name="password"
        className="border border-black text-black"
        type="password"
        placeholder="Password"
      />
      <button type="submit">Register</button>
    </form>
  );
}