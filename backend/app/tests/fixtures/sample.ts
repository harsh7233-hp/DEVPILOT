import { useState, useEffect } from "react";
import { fetchUser } from "../api/user";

export interface UserProps {
  name: string;
  id: number;
}

export function UserCard({ name, id }: UserProps) {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUser(id).then(() => setLoading(false));
  }, [id]);

  return null;
}

export default UserCard;
