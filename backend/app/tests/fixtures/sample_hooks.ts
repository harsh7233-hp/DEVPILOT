import { useState } from "react";
import useSWR from "swr";

export async function fetchData<T>(url: string): Promise<T> {
  const res = await fetch(url);
  return res.json();
}

const useUser = (id: number) => {
  return useSWR(`/api/user/${id}`, () => fetchData(`/api/users/${id}`));
};

export function handleSubmit(data: FormData) {
  console.log("submitting", data);
  return true;
}

export default useUser;
