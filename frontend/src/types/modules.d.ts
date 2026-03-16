declare module 'react-simple-code-editor' {
  import { Component, ReactNode, CSSProperties, HTMLAttributes } from 'react';

  export interface EditorProps extends HTMLAttributes<HTMLDivElement> {
    value: string;
    onValueChange: (value: string) => void;
    highlight: (value: string) => string | ReactNode;
    padding?: number | string;
    tabSize?: number;
    insertSpaces?: boolean;
    ignoreTabKey?: boolean;
    style?: CSSProperties;
    textareaId?: string;
    textareaClassName?: string;
    preClassName?: string;
  }

  export default class Editor extends Component<EditorProps> {}
}
