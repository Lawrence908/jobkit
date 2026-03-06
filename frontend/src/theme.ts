import { createTheme, MantineColorsTuple } from "@mantine/core";

const amber: MantineColorsTuple = [
  "#fffbeb",
  "#fef3c7",
  "#fde68a",
  "#fcd34d",
  "#fbbf24",
  "#f59e0b",
  "#d97706",
  "#b45309",
  "#92400e",
  "#78350f",
];

export const theme = createTheme({
  fontFamily: "DM Sans, system-ui, sans-serif",
  fontFamilyMonospace: "ui-monospace, monospace",
  headings: {
    fontFamily: "Syne, system-ui, sans-serif",
    fontWeight: "700",
  },
  primaryColor: "amber",
  colors: {
    amber,
  },
  radius: {
    xs: "4px",
    sm: "6px",
    md: "10px",
    lg: "14px",
    xl: "18px",
  },
  defaultRadius: "md",
  primaryShade: { light: 5, dark: 5 },
  respectReducedMotion: true,
  components: {
    Button: {
      defaultProps: {
        size: "sm",
      },
    },
    TextInput: {
      defaultProps: {
        size: "sm",
      },
    },
    Select: {
      defaultProps: {
        size: "sm",
      },
    },
    Paper: {
      defaultProps: {
        radius: "md",
        withBorder: true,
      },
    },
  },
});
