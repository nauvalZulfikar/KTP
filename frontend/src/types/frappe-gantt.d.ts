declare module "frappe-gantt" {
  type Task = {
    id: string;
    name: string;
    start: string;
    end: string;
    progress?: number;
    dependencies?: string;
    custom_class?: string;
  };

  type Options = {
    view_mode?: "Quarter Day" | "Half Day" | "Day" | "Week" | "Month";
    bar_height?: number;
    bar_corner_radius?: number;
    padding?: number;
    date_format?: string;
    language?: string;
  };

  export default class Gantt {
    constructor(
      wrapper: HTMLElement | SVGElement | string,
      tasks: Task[],
      options?: Options
    );
    refresh(tasks: Task[]): void;
    change_view_mode(mode: Options["view_mode"]): void;
  }
}

