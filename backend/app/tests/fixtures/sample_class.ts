import React, { type FC } from "react";

interface CardProps {
  title: string;
  children: React.ReactNode;
}

abstract class BaseComponent {
  abstract render(): string;
}

class Card extends BaseComponent implements CardProps {
  title: string;
  children: React.ReactNode;

  constructor(props: CardProps) {
    super();
    this.title = props.title;
    this.children = props.children;
  }

  render(): string {
    return `<div>${this.title}</div>`;
  }
}

export type { CardProps };
export { Card };
export default Card;
