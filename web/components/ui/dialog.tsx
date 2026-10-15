import * as React from 'react';
import { Dialog as DialogPrimitive } from 'radix-ui';
import { X } from 'lucide-react';
import { cn } from 'cn';

import { layout } from '@/lib/layout/styles';

/**
 * Confirmation dialog primitive (shadcn/ui shape over radix-ui's Dialog —
 * same stack note as MT-4.1-01's UI kit). MT-4.2-02 uses it for status
 * transitions; MT-4.2-04 reuses it for token revocation.
 */
const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogClose = DialogPrimitive.Close;

function DialogContent({
  className,
  children,
  onCloseAutoFocus,
  onOpenAutoFocus,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Content>) {
  /*
   * MT-4.11-02 (Section 13.4): focus moves into the dialog on open, is
   * trapped while open, and returns to the opener on close. Radix only
   * restores to a `DialogTrigger` ref — our dialogs are opened by
   * external controls (card Move button, New task, review actions), so
   * capture the active element at open and refocus it at close.
   */
  const openerRef = React.useRef<HTMLElement | null>(null);
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in" />
      <DialogPrimitive.Content
        className={cn(
          // MT-4.11-01: shared phone-safe frame — viewport inset + height
          // cap with internal scroll (visual design unchanged at desktop).
          layout.dialogFrame,
          className,
        )}
        onOpenAutoFocus={(event) => {
          // Fires before focus moves into the content — the opener is
          // still the active element here.
          openerRef.current =
            document.activeElement instanceof HTMLElement ? document.activeElement : null;
          onOpenAutoFocus?.(event);
        }}
        onCloseAutoFocus={(event) => {
          onCloseAutoFocus?.(event);
          if (!event.defaultPrevented) {
            openerRef.current?.focus();
            // Nothing else to focus (no DialogTrigger in these dialogs).
            event.preventDefault();
          }
        }}
        {...props}
      >
        {children}
        <DialogPrimitive.Close
          aria-label="Close"
          className="absolute top-4 right-4 rounded-md p-1 text-muted-foreground hover:text-foreground"
        >
          <X className="size-4" aria-hidden="true" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

function DialogHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('flex flex-col gap-1.5', className)} {...props} />;
}

function DialogFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('flex justify-end gap-2', className)} {...props} />;
}

function DialogTitle(props: React.ComponentProps<typeof DialogPrimitive.Title>) {
  return <DialogPrimitive.Title className="text-lg font-semibold" {...props} />;
}

function DialogDescription(props: React.ComponentProps<typeof DialogPrimitive.Description>) {
  return <DialogPrimitive.Description className="text-sm text-muted-foreground" {...props} />;
}

export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
};
